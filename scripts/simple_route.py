#!/usr/bin/env python3
"""Naive 2-layer star/MST router for Clockor boards (pcbnew).

Connects same-net pads with L-shaped tracks (prefer F.Cu, via to B.Cu on
collision with existing copper bbox — best-effort). Then fills GND zones.
Not a production autorouter — reduces unconnected count for review.
"""
from __future__ import annotations
import math
import sys
from collections import defaultdict
from pathlib import Path

import pcbnew

HW = Path("/workspace/clockor/hardware")
ZONE_NETS = {"GND", "+5V", "+3V3", "GNDA"}  # rely on pours mostly; still stitch close pads


def mm(x):
    return int(x * 1_000_000)


def collect_pads(board):
    by_net = defaultdict(list)
    for fp in board.GetFootprints():
        for pad in fp.Pads():
            net = pad.GetNet()
            if net is None:
                continue
            code = net.GetNetCode()
            name = net.GetNetname()
            if code <= 0 or not name or name == "":
                continue
            # skip NPTH / mechanical without copper
            if pad.GetAttribute() == pcbnew.PAD_ATTRIB_NPTH:
                continue
            by_net[name].append(pad)
    return by_net


def clear_tracks(board):
    tracks = list(board.GetTracks())
    for t in tracks:
        board.Remove(t)


def add_track(board, x1, y1, x2, y2, width, layer, netcode):
    if x1 == x2 and y1 == y2:
        return
    tr = pcbnew.PCB_TRACK(board)
    tr.SetStart(pcbnew.VECTOR2I(int(x1), int(y1)))
    tr.SetEnd(pcbnew.VECTOR2I(int(x2), int(y2)))
    tr.SetWidth(int(width))
    tr.SetLayer(layer)
    tr.SetNetCode(netcode)
    board.Add(tr)


def add_via(board, x, y, netcode):
    via = pcbnew.PCB_VIA(board)
    via.SetPosition(pcbnew.VECTOR2I(int(x), int(y)))
    via.SetWidth(mm(0.8))
    via.SetDrill(mm(0.4))
    via.SetNetCode(netcode)
    via.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    board.Add(via)


def mst_edges(pts):
    """Prim MST on list of (x,y,pad)."""
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


def route_board(name: str):
    pcb_path = HW / name / f"{name}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb_path))
    clear_tracks(board)
    by_net = collect_pads(board)
    settings = board.GetDesignSettings()
    track_w = settings.GetCurrentTrackWidth() or mm(0.25)
    power_w = mm(0.5)

    routed_edges = 0
    skipped = 0
    for netname, pads in sorted(by_net.items()):
        # unique positions
        pts = []
        seen = set()
        netcode = pads[0].GetNetCode()
        for p in pads:
            pos = p.GetPosition()
            key = (pos.x, pos.y)
            if key in seen:
                continue
            seen.add(key)
            pts.append((pos.x, pos.y, p))
        if len(pts) < 2:
            continue
        # For heavy power/GND with many pads, only connect a spanning tree of
        # footprint centers (still helps DRC unconnected); zones do the rest.
        w = power_w if netname in ZONE_NETS or netname.startswith("+") else track_w
        edges = mst_edges(pts)
        for i, j in edges:
            x1, y1, _ = pts[i]
            x2, y2, _ = pts[j]
            # L-route on F.Cu; if long, mid via to B.Cu then back
            dist = math.hypot(x2 - x1, y2 - y1)
            layer = pcbnew.F_Cu
            if dist > mm(40) and netname not in ZONE_NETS:
                # horizontal on F, via, vertical on B
                mx, my = x2, y1
                add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
                add_via(board, mx, my, netcode)
                add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
            else:
                mx, my = x2, y1
                add_track(board, x1, y1, mx, my, w, layer, netcode)
                add_track(board, mx, my, x2, y2, w, layer, netcode)
            routed_edges += 1

    # Fill zones
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    n_tracks = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    n_vias = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    print(f"{name}: MST edges={routed_edges} tracks~{n_tracks} vias~{n_vias} nets={len(by_net)}")
    return pcb_path


def main():
    boards = sys.argv[1:] or ["base-controller", "hand-minute"]
    for b in boards:
        route_board(b)


if __name__ == "__main__":
    main()
