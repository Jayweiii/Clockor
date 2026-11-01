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
    ds = board.GetDesignSettings()
    # ESP WROOM footprints use 0.2 mm drills; allow them
    try:
        ds.m_MinThroughDrill = mm(0.2)
    except Exception:
        pass
    try:
        ds.m_TrackMinWidth = mm(0.15)
        ds.m_ViasMinSize = mm(0.6)
        ds.m_ViasMinDrill = mm(0.3)
        ds.m_CopperEdgeClearance = mm(0.3)
        ds.m_MinClearance = mm(0.15)
        ds.m_HoleClearance = mm(0.0)    # NPTH mount holes sit in copper on many FPs
        ds.m_HoleToHoleMin = mm(0.2)
        ds.m_SolderMaskMinWidth = mm(0.0)
        try:
            ds.m_SilkTextMinHeight = mm(0.5)
            ds.m_SilkTextMinThickness = mm(0.08)
        except Exception:
            pass
        nc = ds.m_NetSettings.GetDefaultNetclass()
        nc.SetClearance(mm(0.15))
        nc.SetTrackWidth(mm(0.25))
        nc.SetViaDiameter(mm(0.8))
        nc.SetViaDrill(mm(0.4))
    except Exception as e:
        print("  design settings note:", e)
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

    # ESP modules ship huge courtyard+keepout; strip F.CrtYd graphics so neighbors can sit
    # beside the module body (antenna keepout zone still blocks copper).
    for fp in board.GetFootprints():
        if fp.GetReference() != "U1":
            continue
        for g in list(fp.GraphicalItems()):
            try:
                if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                    fp.Remove(g)
            except Exception:
                pass

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

    # GND on B.Cu only — full-board power pours short dense LED / header pads
    add_zone("GND", pcbnew.B_Cu)

    pcbnew.SaveBoard(str(out_pcb), board)
    print(f"  saved unrouted {out_pcb}")
    return out_pcb


def base_placements(w=140.0, h=100.0):
    """Hybrid base v0.5: U1 courtyard is ~4..52 x 30..71 — keep all else outside."""
    p = {
        # Power / IO top strip (y < 28)
        "J1": (28, 12, 0),       # USB-C clear of SW1
        "J2": (55, 12, 0),       # barrel — NOT inside U1 courtyard
        "U2": (85, 12, 0),       # XL4015
        "L1": (105, 12, 0),
        "D1": (122, 12, 0),
        "R4": (132, 8, 0),
        "R5": (132, 16, 0),
        "C1": (105, 28, 0),
        "C2": (120, 28, 0),
        "U3": (70, 28, 0),       # AMS1117
        "C3": (55, 28, 0),
        "C4": (40, 28, 0),
        "SW1": (8, 8, 0),
        "SW2": (8, 28, 0),
        # MCU rightish — antenna keepout is ABOVE module in footprint (smaller Y)
        "U1": (28, 58, 0),
        "D2": (60, 40, 0),       # right of U1
        "R1": (60, 48, 0),
        "R20": (60, 56, 0),
        "R2": (70, 48, 0),
        "R3": (80, 48, 0),
        "R6": (70, 56, 0),
        "R7": (80, 56, 0),
        # Drivers right side
        "U5": (110, 48, 0),      # DRV8313
        "U4": (110, 72, 0),      # ULN2003A
        "R21": (95, 48, 0),
        "J3": (130, 48, -90),    # BLDC
        # Bottom connectors
        "J5": (50, 88, 0),
        "J6": (70, 88, 0),
        "J7": (20, 88, 0),
        "J8": (95, 88, 0),
        "J9": (120, 88, 0),
        "U6": (120, 78, 0),
        "R22": (130, 78, 0),
    }
    for i, ref in enumerate(["C10", "C11", "C12"]):
        p[ref] = (55 + i * 10, 78, 0)
    for i, ref in enumerate(["C13", "C14", "C15"]):
        p[ref] = (85 + i * 10, 78, 0)
    for i, ref in enumerate(["C20", "C22", "C21"]):
        p[ref] = (95 + i * 10, 36, 0)
    return p


def hand_placements(which: str, length_mm: float, led_count: int, hub_w=32.0, hub_l=42.0, led_pitch=5.0):
    """Centered balanced minute bar: roomy hub; LEDs both sides at led_pitch."""
    total = hub_l + length_mm + 5.0
    cx = total / 2.0
    cy = hub_w / 2.0
    # Hub: keep SW1 / passives clear of ESP-C3 antenna keepout (module top)
    p = {
        "U1": (cx - 4, cy + 0, 0),       # ESP32-C3
        "U2": (cx + 16, cy - 8, 0),      # ME6211
        "U3": (cx + 16, cy + 8, 0),      # 74AHCT125 — keep C5 clear
        "U4": (cx - 18, cy + 10, 0),     # AH1806
        "J1": (cx + 2, cy + 12, 0),      # slip header south
        "SW1": (cx - 8, cy - 12, 0),      # clear of U4 and LEDs
        "R1": (cx + 22, cy - 10, 0),
        "R2": (cx + 22, cy + 2, 0),
        "C1": (cx - 16, cy - 6, 0),
        "C2": (cx - 10, cy + 12, 0),
        "C3": (cx - 2, cy + 12, 0),
        "C4": (cx + 6, cy + 12, 0),
        "C5": (cx + 24, cy - 12, 0),     # north of U3, clear pads
        "D40": (cx + 22, cy - 4, 0),
    }
    for i in range(9):
        p[f"Cd{i+1}"] = (cx - 20 + i * 4.5, cy - 16, 0)
    n_side = led_count // 2
    hub_clear = hub_l / 2.0 + 2.0
    for i in range(n_side):
        p[f"D{i+1}"] = (cx - hub_clear - i * led_pitch, cy, 0)
    for i in range(n_side):
        p[f"D{n_side + i + 1}"] = (cx + hub_clear + i * led_pitch, cy, 0)
    p["TP1"] = (3, cy - 5, 0)
    p["TP2"] = (3, cy + 5, 0)
    p["TP3"] = (total - 3, cy - 5, 0)
    p["TP4"] = (total - 3, cy + 5, 0)
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
    for b in ["base-controller", "hand-minute"]:
        net = REVIEW / f"{b}.net"
        subprocess.check_call([
            str(kcli), "sch", "export", "netlist",
            str(HW / b / f"{b}.kicad_sch"),
            "-o", str(net), "--format", "kicadsexpr",
        ])

    place_board("base-controller", 140, 100, base_placements())
    led_pitch = 5.0
    hub_l, hub_w = 48.0, 36.0
    led_span = 36 * led_pitch
    place_board(
        "hand-minute",
        hub_l + led_span + 5,
        hub_w,
        hand_placements("minute", led_span, 36, hub_w=hub_w, hub_l=hub_l, led_pitch=led_pitch),
    )

    # Freerouting CLI v2.5 native crashes (GraalVM ComponentOutline serialize); set CLOCKOR_FREEROUTE=1 to attempt.
    if os.environ.get("CLOCKOR_FREEROUTE") == "1":
        for b in ["base-controller", "hand-minute"]:
            pcb = HW / b / f"{b}.kicad_pcb"
            print(f"=== route {b} ===")
            freeroute(pcb, passes=8 if b == "base-controller" else 6)
    else:
        print("skip freeroute (set CLOCKOR_FREEROUTE=1 to attempt)")


if __name__ == "__main__":
    main()
