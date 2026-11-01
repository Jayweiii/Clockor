#!/usr/bin/env python3
"""Careful router: LED spines, pad obstacles, then delete anything that still shorts."""
from __future__ import annotations

import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pcbnew

HW = Path("/workspace/clockor/hardware")
REVIEW = Path("/workspace/clockor/review")
ZONE_NETS = {"GND", "GNDA"}
TRACK_W = 0.2
POWER_W = 0.35
VIA_D = 0.7
VIA_DRILL = 0.35
CLEAR = 0.25  # mm


def mm(x: float) -> int:
    return int(round(x * 1_000_000))


def clear_tracks(board):
    for t in list(board.GetTracks()):
        board.Remove(t)


def add_track(board, x1, y1, x2, y2, width, layer, netcode):
    if int(x1) == int(x2) and int(y1) == int(y2):
        return None
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    tr.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    tr.SetWidth(int(width))
    tr.SetLayer(layer)
    tr.SetNetCode(netcode)
    board.Add(tr)
    return tr


def add_via(board, x, y, netcode):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    via.SetWidth(mm(VIA_D))
    via.SetDrill(mm(VIA_DRILL))
    via.SetNetCode(netcode)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)
    return via


def dist_point_seg(px, py, x1, y1, x2, y2):
    dx, dy = x2 - x1, y2 - y1
    if dx == 0 and dy == 0:
        return math.hypot(px - x1, py - y1)
    t = max(0.0, min(1.0, ((px - x1) * dx + (py - y1) * dy) / float(dx * dx + dy * dy)))
    return math.hypot(px - (x1 + t * dx), py - (y1 + t * dy))


class Obstacles:
    def __init__(self, board):
        self.pads = []
        self.segs = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
        self.vias = []
        for fp in board.GetFootprints():
            for pad in fp.Pads():
                if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                    continue
                net = pad.GetNet()
                code = net.GetNetCode() if net else 0
                pos = pad.GetPosition()
                size = pad.GetSize()
                r = max(size.x, size.y) / 2.0 + mm(0.05)
                self.pads.append((pos.x, pos.y, r, code, fp.GetReference(), pad.GetNumber()))

    def ok_seg(self, x1, y1, x2, y2, layer, netcode, clearance):
        for px, py, r, n, *_ in self.pads:
            if n == netcode:
                continue
            if dist_point_seg(px, py, x1, y1, x2, y2) < r + clearance:
                return False
        for sx1, sy1, sx2, sy2, n in self.segs[layer]:
            if n == netcode:
                continue
            # bbox inflate
            ax0, ax1 = min(x1, x2) - clearance, max(x1, x2) + clearance
            ay0, ay1 = min(y1, y2) - clearance, max(y1, y2) + clearance
            bx0, bx1 = min(sx1, sx2) - clearance, max(sx1, sx2) + clearance
            by0, by1 = min(sy1, sy2) - clearance, max(sy1, sy2) + clearance
            if not (ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0):
                return False
        for vx, vy, n in self.vias:
            if n == netcode:
                continue
            if dist_point_seg(vx, vy, x1, y1, x2, y2) < clearance + mm(VIA_D / 2):
                return False
        return True

    def ok_via(self, x, y, netcode, clearance):
        for px, py, r, n, *_ in self.pads:
            if n == netcode:
                continue
            if math.hypot(px - x, py - y) < r + clearance:
                return False
        for vx, vy, n in self.vias:
            if n == netcode:
                continue
            if math.hypot(vx - x, vy - y) < clearance + mm(VIA_D):
                return False
        return True

    def add_seg(self, x1, y1, x2, y2, layer, netcode):
        self.segs[layer].append((x1, y1, x2, y2, netcode))

    def add_via(self, x, y, netcode):
        self.vias.append((x, y, netcode))


def try_route(board, obs, x1, y1, x2, y2, w, netcode, clearance):
    pats = []
    if x1 == x2 or y1 == y2:
        pats += [[(x1, y1, x2, y2, pcbnew.F_Cu)], [(x1, y1, x2, y2, pcbnew.B_Cu)]]
    pats += [
        [(x1, y1, x2, y1, pcbnew.F_Cu), (x2, y1, x2, y2, pcbnew.F_Cu)],
        [(x1, y1, x1, y2, pcbnew.F_Cu), (x1, y2, x2, y2, pcbnew.F_Cu)],
        [(x1, y1, x2, y1, pcbnew.B_Cu), (x2, y1, x2, y2, pcbnew.B_Cu)],
        [(x1, y1, x1, y2, pcbnew.B_Cu), (x1, y2, x2, y2, pcbnew.B_Cu)],
        "VIA_HV",
        "VIA_VH",
    ]
    for pat in pats:
        if pat == "VIA_HV":
            mx, my = x2, y1
            if not obs.ok_via(mx, my, netcode, clearance):
                continue
            if not obs.ok_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode, clearance):
                continue
            if not obs.ok_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode, clearance):
                continue
            add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
            add_via(board, mx, my, netcode)
            add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
            obs.add_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode)
            obs.add_via(mx, my, netcode)
            obs.add_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode)
            return True
        if pat == "VIA_VH":
            mx, my = x1, y2
            if not obs.ok_via(mx, my, netcode, clearance):
                continue
            if not obs.ok_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode, clearance):
                continue
            if not obs.ok_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode, clearance):
                continue
            add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
            add_via(board, mx, my, netcode)
            add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
            obs.add_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode)
            obs.add_via(mx, my, netcode)
            obs.add_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode)
            return True
        if all(obs.ok_seg(a, b, c, d, layer, netcode, clearance) for a, b, c, d, layer in pat):
            for a, b, c, d, layer in pat:
                add_track(board, a, b, c, d, w, layer, netcode)
                obs.add_seg(a, b, c, d, layer, netcode)
            return True
    return False


def pad_pos(fp, num):
    for pad in fp.Pads():
        if pad.GetNumber() == str(num):
            p = pad.GetPosition()
            return p.x, p.y, pad.GetNetCode()
    return None


def route_led_bar(board, obs, clearance):
    """APA102-2020: pad 1=DI, 2=CI, 3=VDD(+5V), 4=NC?, 5=DO, 6=GND — verify via nets.
    Use net names on pads rather than assuming numbers."""
    leds = []
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        m = re.fullmatch(r"D(\d+)", ref)
        if not m:
            continue
        n = int(m.group(1))
        if n >= 40:  # TVS etc
            continue
        leds.append((n, fp))
    leds.sort()
    if len(leds) < 2:
        return 0
    routed = 0
    # Build pad role by net name
    def roles(fp):
        r = {}
        for pad in fp.Pads():
            net = pad.GetNet()
            if not net:
                continue
            name = net.GetNetname()
            pos = pad.GetPosition()
            if name in ("+5V",):
                r["vdd"] = (pos.x, pos.y, net.GetNetCode())
            elif name in ("GND", "GNDA"):
                r["gnd"] = (pos.x, pos.y, net.GetNetCode())
            elif "DI" in name or name.endswith("_DI") or "LED_DI" in name or name == "DI":
                r["di"] = (pos.x, pos.y, net.GetNetCode())
            elif "DO" in name or name.endswith("_DO") or "LED_DO" in name:
                r["do"] = (pos.x, pos.y, net.GetNetCode())
            elif "CI" in name or name.endswith("_CI"):
                r["ci"] = (pos.x, pos.y, net.GetNetCode())
            elif "CO" in name or name.endswith("_CO"):
                r["co"] = (pos.x, pos.y, net.GetNetCode())
        # fallback: classify by unique nets among signal pads
        return r

    role_list = [(n, fp, roles(fp)) for n, fp in leds]
    # Daisy-chain: same net shared by DO of Di and DI of Di+1 — connect those two pads only
    # Find nets with exactly 2 LED pads
    net_pads = defaultdict(list)
    for n, fp, r in role_list:
        for pad in fp.Pads():
            net = pad.GetNet()
            if not net or net.GetNetCode() <= 0:
                continue
            name = net.GetNetname()
            if name in ("+5V", "GND", "GNDA") or not name:
                continue
            pos = pad.GetPosition()
            net_pads[name].append((pos.x, pos.y, net.GetNetCode(), fp.GetReference()))

    for name, pts in net_pads.items():
        # unique
        uniq = {}
        for x, y, c, ref in pts:
            uniq[(x, y)] = (x, y, c)
        pts2 = list(uniq.values())
        if len(pts2) != 2:
            continue
        (x1, y1, c), (x2, y2, _) = pts2
        w = mm(TRACK_W)
        # prefer direct if almost aligned
        if try_route(board, obs, x1, y1, x2, y2, w, c, clearance):
            routed += 1

    # +5V spine above LEDs, GND vias to zone
    vdd_pts = []
    gnd_pts = []
    for n, fp, r in role_list:
        if "vdd" in r:
            vdd_pts.append(r["vdd"])
        if "gnd" in r:
            gnd_pts.append(r["gnd"])
    if vdd_pts:
        # spine Y = min pad Y - 2.5mm (above in board coords if Y increases down — use mean - offset)
        ys = [p[1] for p in vdd_pts]
        spine_y = min(ys) - mm(2.8)
        netcode = vdd_pts[0][2]
        w = mm(POWER_W)
        # stubs + spine chain along sorted X
        stubs = []
        for x, y, c in sorted(vdd_pts, key=lambda p: p[0]):
            if try_route(board, obs, x, y, x, spine_y, w, c, clearance):
                routed += 1
                stubs.append((x, spine_y, c))
            else:
                # try slightly different spine
                for dy in (mm(3.2), mm(2.2), -mm(2.8), -mm(3.2)):
                    sy = y + dy if dy < 0 else min(ys) - abs(dy)
                    # actually use y-based
                    sy = y - mm(2.8) if dy > 0 else y + mm(2.8)
                    if try_route(board, obs, x, y, x, sy, w, c, clearance):
                        routed += 1
                        stubs.append((x, sy, c))
                        break
        stubs.sort()
        for i in range(len(stubs) - 1):
            x1, y1, c = stubs[i]
            x2, y2, _ = stubs[i + 1]
            if abs(y1 - y2) > mm(0.1):
                # normalize to first spine
                if try_route(board, obs, x2, y2, x2, y1, w, c, clearance):
                    routed += 1
                    y2 = y1
            if try_route(board, obs, x1, y1, x2, y1, w, c, clearance):
                routed += 1

    # GND: via at each pad (zone on B.Cu)
    for x, y, c in gnd_pts:
        # short dogbone then via if needed — via on pad OK for PTH; for SMD offset
        vx, vy = x, y + mm(1.2)
        if obs.ok_via(vx, vy, c, clearance) and obs.ok_seg(x, y, vx, vy, pcbnew.F_Cu, c, clearance):
            add_track(board, x, y, vx, vy, mm(POWER_W), pcbnew.F_Cu, c)
            add_via(board, vx, vy, c)
            obs.add_seg(x, y, vx, vy, pcbnew.F_Cu, c)
            obs.add_via(vx, vy, c)
            routed += 1
        elif obs.ok_via(x, y - mm(1.2), c, clearance):
            vx, vy = x, y - mm(1.2)
            if obs.ok_seg(x, y, vx, vy, pcbnew.F_Cu, c, clearance):
                add_track(board, x, y, vx, vy, mm(POWER_W), pcbnew.F_Cu, c)
                add_via(board, vx, vy, c)
                obs.add_seg(x, y, vx, vy, pcbnew.F_Cu, c)
                obs.add_via(vx, vy, c)
                routed += 1
    return routed


def mst_edges(pts):
    n = len(pts)
    if n < 2:
        return []
    used = [False] * n
    used[0] = True
    edges = []
    for _ in range(n - 1):
        best = None
        for i in range(n):
            if not used[i]:
                continue
            for j in range(n):
                if used[j]:
                    continue
                d = (pts[i][0] - pts[j][0]) ** 2 + (pts[i][1] - pts[j][1]) ** 2
                if best is None or d < best[0]:
                    best = (d, i, j)
        if best is None:
            break
        _, i, j = best
        used[j] = True
        edges.append((i, j))
    return edges


def collect_by_net(board):
    by = defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNet()
            if not net or net.GetNetCode() <= 0:
                continue
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            by[net.GetNetname()].append(pad)
    return by


def ensure_gnd_zone(board):
    net = board.FindNet("GND")
    if not net or net.GetNetCode() <= 0:
        return
    for z in list(board.Zones()):
        board.Remove(z)
    bb = board.GetBoardEdgesBoundingBox()
    zone = pcbnew.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetIsFilled(False)
    try:
        zone.SetLocalClearance(mm(0.3))
        zone.SetMinThickness(mm(0.25))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    except Exception:
        pass
    chain = pcbnew.SHAPE_LINE_CHAIN()
    m = mm(1.0)
    chain.Append(bb.GetLeft() + m, bb.GetTop() + m)
    chain.Append(bb.GetRight() - m, bb.GetTop() + m)
    chain.Append(bb.GetRight() - m, bb.GetBottom() - m)
    chain.Append(bb.GetLeft() + m, bb.GetBottom() - m)
    chain.SetClosed(True)
    zone.Outline().AddOutline(chain)
    board.Add(zone)


def shrink_silk(board):
    for fp in board.GetFootprints():
        for t in (fp.Reference(), fp.Value()):
            try:
                t.SetVisible(False)
            except Exception:
                pass


def remove_shorting_tracks(pcb_path: Path, max_iters=8):
    """Run DRC, delete tracks mentioned in shorting_items, repeat."""
    kcli = Path("/workspace/tools/kicad/kicad-cli")
    if not kcli.exists():
        kcli = Path("/workspace/tools/kicad/squashfs-root/usr/bin/kicad-cli")
    for it in range(max_iters):
        board = pcbnew.LoadBoard(str(pcb_path))
        rpt = REVIEW / f"_short_iter_{pcb_path.stem}.rpt"
        subprocess.run(
            [str(kcli), "pcb", "drc", "--severity-all", "-o", str(rpt), str(pcb_path)],
            capture_output=True,
        )
        text = rpt.read_text() if rpt.exists() else ""
        blocks = re.split(r"\n(?=\[)", text)
        kill = []  # (x,y) approx track midpoints or pad refs — match tracks by coords
        n_short = 0
        for b in blocks:
            if not b.startswith("[shorting_items]"):
                continue
            n_short += 1
            for m in re.finditer(
                r"@\(([-\d.]+)\s*mm,\s*([-\d.]+)\s*mm\):\s*Track", b
            ):
                kill.append((float(m.group(1)), float(m.group(2))))
        if n_short == 0:
            print(f"  short-clean {pcb_path.name}: 0 shorts at iter {it}")
            return 0
        if not kill:
            print(f"  short-clean {pcb_path.name}: {n_short} shorts but no track coords (pad-pad?) iter {it}")
            return n_short
        removed = 0
        for t in list(board.GetTracks()):
            if t.GetClass() != "PCB_TRACK":
                continue
            s, e = t.GetStart(), t.GetEnd()
            mx = (s.x + e.x) / 2 / 1e6
            my = (s.y + e.y) / 2 / 1e6
            sx, sy = s.x / 1e6, s.y / 1e6
            ex, ey = e.x / 1e6, e.y / 1e6
            for kx, ky in kill:
                if (
                    math.hypot(mx - kx, my - ky) < 0.8
                    or math.hypot(sx - kx, sy - ky) < 0.5
                    or math.hypot(ex - kx, ey - ky) < 0.5
                ):
                    board.Remove(t)
                    removed += 1
                    break
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(str(pcb_path), board)
        print(f"  short-clean iter {it}: shorts={n_short} removed_tracks={removed}")
        if removed == 0:
            return n_short
    return n_short


def route_board(name: str):
    pcb_path = HW / name / f"{name}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb_path))
    clear_tracks(board)
    ensure_gnd_zone(board)
    obs = Obstacles(board)
    clearance = mm(CLEAR)
    routed = 0

    if name == "hand-minute":
        routed += route_led_bar(board, obs, clearance)

    by = collect_by_net(board)
    # Skip power MST on hand (spines/vias done); on base allow short stitches only
    for netname, pads in sorted(by.items(), key=lambda kv: (kv[0] in ("+5V", "GND", "GNDA", "+3V3") or "VIN" in kv[0], len(kv[1]), kv[0])):
        if name == "hand-minute" and (netname in ("+5V", "GND", "GNDA") or netname.startswith("+")):
            continue
        # skip nets already likely daisy-chained (exactly 2 pads) — try them first actually
        pts = []
        seen = set()
        for p in pads:
            pos = p.GetPosition()
            key = (pos.x, pos.y)
            if key in seen:
                continue
            seen.add(key)
            pts.append((pos.x, pos.y, p.GetNetCode()))
        if len(pts) < 2:
            continue
        netcode = pts[0][2]
        w = mm(POWER_W if netname in ("+5V", "+3V3", "GND") or "VIN" in netname else TRACK_W)
        max_d = mm(5 if netname in ("+5V", "+3V3", "GND") or "VIN" in netname else 25)
        for i, j in mst_edges(pts):
            x1, y1, c = pts[i]
            x2, y2, _ = pts[j]
            if math.hypot(x2 - x1, y2 - y1) > max_d:
                continue
            if try_route(board, obs, x1, y1, x2, y2, w, c, clearance):
                routed += 1

    # GND vias near remaining GND pads (base)
    if name == "base-controller":
        for pad in by.get("GND", []):
            pos = pad.GetPosition()
            c = pad.GetNetCode()
            for dx, dy in ((0, 1.5), (0, -1.5), (1.5, 0), (-1.5, 0)):
                vx, vy = pos.x + mm(dx), pos.y + mm(dy)
                if obs.ok_via(vx, vy, c, clearance) and obs.ok_seg(
                    pos.x, pos.y, vx, vy, pcbnew.F_Cu, c, clearance
                ):
                    add_track(board, pos.x, pos.y, vx, vy, mm(POWER_W), pcbnew.F_Cu, c)
                    add_via(board, vx, vy, c)
                    obs.add_seg(pos.x, pos.y, vx, vy, pcbnew.F_Cu, c)
                    obs.add_via(vx, vy, c)
                    routed += 1
                    break

    shrink_silk(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    n_tracks = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    n_vias = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    print(f"{name}: routed_ops={routed} tracks={n_tracks} vias={n_vias}")
    shorts = remove_shorting_tracks(pcb_path)
    return shorts


def main():
    REVIEW.mkdir(exist_ok=True)
    boards = sys.argv[1:] or ["base-controller", "hand-minute"]
    for b in boards:
        route_board(b)


if __name__ == "__main__":
    main()
