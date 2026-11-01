#!/usr/bin/env python3
"""Build placed PCBs from sexpr netlists, Freeroute via Specctra DSN/SES, save."""
from __future__ import annotations

import os
import re
import subprocess
import sys
from pathlib import Path

# AppImage pcbnew
KROOT = Path("/workspace/tools/kicad/squashfs-root")
os.environ.setdefault(
    "LD_LIBRARY_PATH",
    f"/workspace/tools/syslibs/usr/lib/x86_64-linux-gnu:"
    f"{KROOT}/usr/lib/x86_64-linux-gnu:{KROOT}/lib/x86_64-linux-gnu:"
    f"{KROOT}/usr/lib:{KROOT}/lib",
)
os.environ.setdefault("PYTHONPATH", str(KROOT / "usr/lib/python3/dist-packages"))
os.environ.setdefault("KICAD9_FOOTPRINT_DIR", str(KROOT / "usr/share/kicad/footprints"))

# Re-exec under AppImage python if needed
if sys.version_info[:2] != (3, 10):
    py = str(KROOT / "usr/bin/python3.10")
    os.execve(py, [py, __file__, *sys.argv[1:]], os.environ)

import pcbnew  # noqa: E402

ROOT = Path("/workspace/clockor")
HW = ROOT / "hardware"
REVIEW = ROOT / "review"
FREEROUTING = Path("/workspace/pov-clock-pcb/tools/freerouting-cli")
FP_DIR = Path(os.environ["KICAD9_FOOTPRINT_DIR"])
FP_ALIASES = {
    "Capacitor_SMD:CP_Elec_10x10.2": "Capacitor_SMD:CP_Elec_10x10",
    "Inductor_SMD:L_12.5x12.5_H6": "Inductor_SMD:L_TaiTech_TMPC1265_13.5x12.5mm",
}
EXTRA_PRETTY = {
    "Espressif": HW / "libs" / "Espressif.pretty",
    "Clockor": HW / "libs" / "Clockor.pretty",
}


def parse_netlist(path: Path):
    text = path.read_text()
    comps = []
    for m in re.finditer(
        r'\(comp \(ref "([^"]+)"\)\s*\(value "([^"]*)"\)\s*\(footprint "([^"]*)"\)',
        text,
    ):
        ref, val, fp = m.group(1), m.group(2), m.group(3)
        if not fp or ref.startswith("#"):
            continue
        comps.append({"ref": ref, "value": val, "footprint": fp})

    nets = []
    for nm in re.finditer(
        r'\(net \(code "(\d+)"\) \(name "([^"]*)"\)[^)]*(?:\([^)]*\))*\s*((?:\(node[^)]*\)\s*)*)\)',
        text,
    ):
        code, name, nodes_blob = nm.group(1), nm.group(2), nm.group(3)
        nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', nodes_blob)
        nets.append({"code": int(code), "name": name, "nodes": nodes})

    # More robust net parse: block by block
    nets = []
    for block in re.finditer(r"\(net \(code \"(\d+)\"\) \(name \"([^\"]*)\"\)(.*?)(?=\n    \(net |\n  \)\n)", text, re.S):
        code, name, body = int(block.group(1)), block.group(2), block.group(3)
        nodes = re.findall(r'\(node \(ref "([^"]+)"\) \(pin "([^"]+)"\)', body)
        nets.append({"code": code, "name": name, "nodes": nodes})
    return comps, nets


def resolve_pretty(lib: str) -> Path:
    if lib in EXTRA_PRETTY:
        return EXTRA_PRETTY[lib]
    p = FP_DIR / f"{lib}.pretty"
    if p.exists():
        return p
    raise FileNotFoundError(f"Footprint lib not found: {lib}")


def load_fp(lib: str, name: str):
    plugin = pcbnew.PCB_IO_MGR.PluginFind(pcbnew.PCB_IO_MGR.KICAD_SEXP)
    path = str(resolve_pretty(lib))
    fp = plugin.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError(f"FootprintLoad failed: {lib}:{name}")
    return fp


def mm(x: float) -> int:
    return int(pcbnew.FromMM(x))


def add_rect_edge(board, x0, y0, x1, y1):
    """Add Edge.Cuts rectangle as 4 segments."""
    pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1), (x0, y0)]
    for (a, b), (c, d) in zip(pts, pts[1:]):
        seg = pcbnew.PCB_SHAPE(board)
        seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
        seg.SetLayer(pcbnew.Edge_Cuts)
        seg.SetStart(pcbnew.VECTOR2I(mm(a), mm(b)))
        seg.SetEnd(pcbnew.VECTOR2I(mm(c), mm(d)))
        seg.SetWidth(mm(0.1))
        board.Add(seg)


def ensure_net(board, name: str):
    if not name or name == "":
        return board.GetNetInfo().GetNetItem(0)
    ni = board.FindNet(name)
    if ni is not None and ni.GetNetCode() > 0:
        return ni
    ni = pcbnew.NETINFO_ITEM(board, name)
    board.Add(ni)
    return ni


def place_board(board_name: str, width_mm: float, height_mm: float, placements: dict):
    """placements: ref -> (x_mm, y_mm, rot_deg)"""
    net_path = REVIEW / f"{board_name}.net"
    out_pcb = HW / board_name / f"{board_name}.kicad_pcb"
    comps, nets = parse_netlist(net_path)
    print(f"{board_name}: {len(comps)} comps, {len(nets)} nets")

    board = pcbnew.NewBoard(str(out_pcb))
    board.GetDesignSettings().SetAuxOrigin(pcbnew.VECTOR2I(0, 0))
    add_rect_edge(board, 0, 0, width_mm, height_mm)

    # Create nets first
    net_by_name = {}
    for n in nets:
        ni = ensure_net(board, n["name"])
        net_by_name[n["name"]] = ni

    # Map (ref, pin) -> net name
    pin_net = {}
    for n in nets:
        for ref, pin in n["nodes"]:
            pin_net[(ref, pin)] = n["name"]

    missing_place = []
    for c in comps:
        ref = c["ref"]
        fpid = FP_ALIASES.get(c["footprint"], c["footprint"])
        lib, name = fpid.split(":", 1)
        try:
            fp = load_fp(lib, name)
        except Exception as e:
            print(f"  FAIL load {ref} {c['footprint']}: {e}")
            continue
        fp.SetReference(ref)
        fp.SetValue(c["value"])
        if ref in placements:
            x, y, rot = placements[ref]
        else:
            missing_place.append(ref)
            # dump in a park area
            idx = len(missing_place)
            x = 5 + (idx % 20) * 5
            y = height_mm + 10 + (idx // 20) * 5
            rot = 0
        fp.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y)))
        fp.SetOrientation(pcbnew.EDA_ANGLE(rot, pcbnew.DEGREES_T))
        # Assign pad nets
        for pad in fp.Pads():
            pname = pad.GetNumber()
            nname = pin_net.get((ref, pname))
            if nname:
                ni = net_by_name.get(nname) or ensure_net(board, nname)
                pad.SetNet(ni)
        board.Add(fp)

    if missing_place:
        print(f"  parked without explicit place: {missing_place[:20]}{'...' if len(missing_place)>20 else ''}")

    # Copper zones for GND / +5V / +3V3 (filled later)
    def add_zone(netname, layer):
        if netname not in net_by_name:
            return
        zone = pcbnew.ZONE(board)
        zone.SetNet(net_by_name[netname])
        zone.SetLayer(layer)
        zone.SetIsFilled(False)
        chain = pcbnew.SHAPE_LINE_CHAIN()
        margin = 0.5
        for x, y in [
            (margin, margin),
            (width_mm - margin, margin),
            (width_mm - margin, height_mm - margin),
            (margin, height_mm - margin),
        ]:
            chain.Append(mm(x), mm(y))
        chain.SetClosed(True)
        zone.Outline().AddOutline(chain)
        board.Add(zone)

    add_zone("GND", pcbnew.F_Cu)
    add_zone("GND", pcbnew.B_Cu)

    pcbnew.SaveBoard(str(out_pcb), board)
    print(f"  saved unrouted {out_pcb}")
    return out_pcb


def base_placements(w=120.0, h=90.0):
    """Spaced placements for base controller (all inside 120x90)."""
    p = {
        "J1": (15, 12, 0),
        "J2": (8, 45, 0),
        "U2": (45, 14, 0),
        "L1": (62, 14, 0),
        "D1": (78, 14, 0),
        "R4": (90, 10, 0),
        "R5": (90, 16, 0),
        "C1": (45, 28, 0),
        "C2": (62, 28, 0),
        "U3": (95, 14, 0),
        "C3": (108, 10, 0),
        "C4": (108, 18, 0),
        "SW1": (20, 28, 0),
        "SW2": (30, 28, 0),
        "U1": (35, 55, 0),
        "D2": (18, 55, 0),
        "R1": (18, 62, 0),
        "R_EN": (18, 68, 0),
        "R2": (58, 42, 0),
        "R3": (66, 42, 0),
        "U4": (70, 55, 0),
        "U5": (95, 40, 0),
        "U6": (95, 68, 0),
        "R_M1F": (80, 40, 0),
        "R_M2F": (80, 68, 0),
        "J3": (112, 40, 0),
        "J4": (112, 68, 0),
        "J5": (55, 82, 0),
        "J6": (70, 82, 0),
        "J7": (20, 82, 0),
        "J8": (35, 82, 0),
    }
    for i, ref in enumerate(["C10", "C11", "C12", "C13", "C14", "C15"]):
        p[ref] = (22 + i * 5, 72, 0)
    for i, ref in enumerate(["C_M1_CP", "C_M1_V3", "C_M1_VCP"]):
        p[ref] = (80 + i * 5, 32, 0)
    for i, ref in enumerate(["C_M2_CP", "C_M2_V3", "C_M2_VCP"]):
        p[ref] = (80 + i * 5, 78, 0)
    return p


def hand_placements(which: str, length_mm: float, led_count: int, hub_w=22.0, hub_l=28.0):
    p = {
        "U1": (14, 8, 0),
        "U2": (14, 16, 0),
        "U3": (14, 4, 0),
        "J1": (4, 11, -90),
        "SW1": (22, 4, 0),
        "R1": (22, 8, 0),
        "C1": (22, 12, 0),
        "C2": (22, 16, 0),
        "C3": (8, 18, 0),
        "C4": (12, 18, 0),
    }
    for i in range(9):
        p[f"Cd{i+1}"] = (hub_l + 2 + i * 12, hub_w - 3, 0)
    # LEDs along arm centerline
    for i in range(led_count):
        p[f"D{i+1}"] = (hub_l + 3.5 + i * 3.5, hub_w / 2, 0)
    return p


def freeroute(pcb_path: Path, passes: int = 30):
    dsn = pcb_path.with_suffix(".dsn")
    ses = pcb_path.with_suffix(".ses")
    board = pcbnew.LoadBoard(str(pcb_path))
    ok = pcbnew.ExportSpecctraDSN(board, str(dsn))
    print(f"  DSN export {ok} -> {dsn}")
    if not ok or not dsn.exists():
        return False
    if ses.exists():
        ses.unlink()
    cmd = [
        "xvfb-run", "-a",
        str(FREEROUTING),
        "-de", str(dsn),
        "-do", str(ses),
        "-mp", str(passes),
        "-mt", "4",
        "-l", "en",
    ]
    print("  freerouting:", " ".join(cmd))
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=720)
    print(r.stdout[-2000:] if r.stdout else "")
    if r.returncode != 0:
        print("  freerouting stderr:", (r.stderr or "")[-1500:])
        return False
    if not ses.exists():
        print("  no SES produced")
        return False
    board = pcbnew.LoadBoard(str(pcb_path))
    ok = pcbnew.ImportSpecctraSES(board, str(ses))
    print(f"  SES import {ok}")
    # Fill zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    # counts
    tracks = sum(1 for _ in board.GetTracks())
    print(f"  tracks/vias items: {tracks}")
    return True


def main():
    REVIEW.mkdir(exist_ok=True)
    # Ensure netlists exist
    kcli = Path("/workspace/tools/kicad/kicad-cli")
    for b in ["base-controller", "hand-minute", "hand-hour"]:
        net = REVIEW / f"{b}.net"
        if not net.exists():
            subprocess.check_call([
                str(kcli), "sch", "export", "netlist",
                str(HW / b / f"{b}.kicad_sch"),
                "-o", str(net), "--format", "kicadsexpr",
            ])

    place_board("base-controller", 120, 90, base_placements())
    place_board(
        "hand-minute",
        28 + 36 * 3.5 + 5,
        22,
        hand_placements("minute", 36 * 3.5, 36),
    )
    place_board(
        "hand-hour",
        28 + 30 * 3.5 + 5,
        22,
        hand_placements("hour", 30 * 3.5, 30),
    )

    for b in ["base-controller", "hand-minute", "hand-hour"]:
        pcb = HW / b / f"{b}.kicad_pcb"
        print(f"=== route {b} ===")
        freeroute(pcb, passes=8 if b == "base-controller" else 6)


if __name__ == "__main__":
    main()
