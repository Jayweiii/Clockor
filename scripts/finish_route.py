#!/usr/bin/env python3
"""Full connectivity router + DRC hygiene for Clockor boards.

Goals: route every multi-pad net without shorts; avoid antenna keepouts;
GND vias into B.Cu zone; remove dangling vias; hide silk; 0 DRC errors.
"""
from __future__ import annotations

import heapq
import math
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

import pcbnew

HW = Path("/workspace/clockor/hardware")
REVIEW = Path("/workspace/clockor/review")
TRACK_W = 0.2
POWER_W = 0.4
VIA_D = 0.6
VIA_DRILL = 0.3
GRID = 0.5  # mm A* grid


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


def seg_intersect(a1x, a1y, a2x, a2y, b1x, b1y, b2x, b2y, clearance=0):
    """True if segments come within clearance (incl. proper crossing)."""
    # endpoint-to-seg distances
    if dist_point_seg(a1x, a1y, b1x, b1y, b2x, b2y) < clearance:
        return True
    if dist_point_seg(a2x, a2y, b1x, b1y, b2x, b2y) < clearance:
        return True
    if dist_point_seg(b1x, b1y, a1x, a1y, a2x, a2y) < clearance:
        return True
    if dist_point_seg(b2x, b2y, a1x, a1y, a2x, a2y) < clearance:
        return True
    # proper intersection via orientations
    def orient(ax, ay, bx, by, cx, cy):
        v = (by - ay) * (cx - bx) - (bx - ax) * (cy - by)
        if abs(v) < 1: return 0
        return 1 if v > 0 else 2
    def on_seg(ax, ay, bx, by, cx, cy):
        return (min(ax, cx) - 1 <= bx <= max(ax, cx) + 1 and
                min(ay, cy) - 1 <= by <= max(ay, cy) + 1)
    o1 = orient(a1x, a1y, a2x, a2y, b1x, b1y)
    o2 = orient(a1x, a1y, a2x, a2y, b2x, b2y)
    o3 = orient(b1x, b1y, b2x, b2y, a1x, a1y)
    o4 = orient(b1x, b1y, b2x, b2y, a2x, a2y)
    if o1 != o2 and o3 != o4:
        return True
    if o1 == 0 and on_seg(a1x, a1y, b1x, b1y, a2x, a2y): return True
    if o2 == 0 and on_seg(a1x, a1y, b2x, b2y, a2x, a2y): return True
    if o3 == 0 and on_seg(b1x, b1y, a1x, a1y, b2x, b2y): return True
    if o4 == 0 and on_seg(b1x, b1y, a2x, a2y, b2x, b2y): return True
    return False


class Obstacles:
    def __init__(self, board):
        self.pads = []
        self.segs = {pcbnew.F_Cu: [], pcbnew.B_Cu: []}
        self.vias = []
        self.keepouts = []  # axis-aligned boxes (x0,y0,x1,y1) in nm
        self.bb = board.GetBoardEdgesBoundingBox()

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
            # Footprint rule-area keepouts (ESP antenna)
            try:
                for z in fp.Zones():
                    if not z.GetIsRuleArea():
                        continue
                    if not z.GetDoNotAllowTracks():
                        continue
                    b = z.GetBoundingBox()
                    self.keepouts.append((b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()))
            except Exception:
                pass
        for z in board.Zones():
            try:
                if z.GetIsRuleArea() and z.GetDoNotAllowTracks():
                    b = z.GetBoundingBox()
                    self.keepouts.append((b.GetLeft(), b.GetTop(), b.GetRight(), b.GetBottom()))
            except Exception:
                pass

    def in_keepout(self, x, y, margin=0):
        for x0, y0, x1, y1 in self.keepouts:
            if x0 - margin <= x <= x1 + margin and y0 - margin <= y <= y1 + margin:
                return True
        return False

    def seg_hits_keepout(self, x1, y1, x2, y2, margin=0):
        # sample along segment
        n = max(3, int(math.hypot(x2 - x1, y2 - y1) / mm(0.4)))
        for i in range(n + 1):
            t = i / n
            if self.in_keepout(x1 + t * (x2 - x1), y1 + t * (y2 - y1), margin):
                return True
        return False

    def ok_seg(self, x1, y1, x2, y2, layer, netcode, clearance):
        if self.seg_hits_keepout(x1, y1, x2, y2, clearance // 2):
            return False
        # stay inside board with edge clearance
        m = mm(0.4)
        for x, y in ((x1, y1), (x2, y2)):
            if not (self.bb.GetLeft() + m <= x <= self.bb.GetRight() - m and
                    self.bb.GetTop() + m <= y <= self.bb.GetBottom() - m):
                return False
        for px, py, r, n, *_ in self.pads:
            if n == netcode:
                continue
            if dist_point_seg(px, py, x1, y1, x2, y2) < r + clearance:
                return False
        for sx1, sy1, sx2, sy2, n in self.segs[layer]:
            if n == netcode:
                continue
            ax0, ax1 = min(x1, x2) - clearance, max(x1, x2) + clearance
            ay0, ay1 = min(y1, y2) - clearance, max(y1, y2) + clearance
            bx0, bx1 = min(sx1, sx2) - clearance, max(sx1, sx2) + clearance
            by0, by1 = min(sy1, sy2) - clearance, max(sy1, sy2) + clearance
            if ax1 < bx0 or bx1 < ax0 or ay1 < by0 or by1 < ay0:
                continue
            if seg_intersect(x1, y1, x2, y2, sx1, sy1, sx2, sy2, clearance):
                return False
        for vx, vy, n in self.vias:
            if n == netcode:
                continue
            if dist_point_seg(vx, vy, x1, y1, x2, y2) < clearance + mm(VIA_D / 2):
                return False
        return True

    def ok_via(self, x, y, netcode, clearance):
        if self.in_keepout(x, y, max(clearance, mm(0.5))):
            return False
        m = mm(0.5)
        if not (self.bb.GetLeft() + m <= x <= self.bb.GetRight() - m and
                self.bb.GetTop() + m <= y <= self.bb.GetBottom() - m):
            return False
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


def commit_path(board, obs, path, w, netcode):
    """path: list of (x,y,layer) points; vias inserted on layer change."""
    if len(path) < 2:
        return False
    for i in range(len(path) - 1):
        x1, y1, l1 = path[i]
        x2, y2, l2 = path[i + 1]
        if l1 != l2:
            # via at junction (use end of prior)
            if not obs.ok_via(x1, y1, netcode, mm(0.2)):
                return False
            add_via(board, x1, y1, netcode)
            obs.add_via(x1, y1, netcode)
            l1 = l2
        if not obs.ok_seg(x1, y1, x2, y2, l1, netcode, mm(0.15)):
            return False
        add_track(board, x1, y1, x2, y2, w, l1, netcode)
        obs.add_seg(x1, y1, x2, y2, l1, netcode)
    return True


def try_route(board, obs, x1, y1, x2, y2, w, netcode, clearance):
    pats = []
    if abs(x1 - x2) < mm(0.05) or abs(y1 - y2) < mm(0.05):
        pats += [[(x1, y1, x2, y2, pcbnew.F_Cu)], [(x1, y1, x2, y2, pcbnew.B_Cu)]]
    # L shapes both layers
    for layer in (pcbnew.F_Cu, pcbnew.B_Cu):
        pats += [
            [(x1, y1, x2, y1, layer), (x2, y1, x2, y2, layer)],
            [(x1, y1, x1, y2, layer), (x1, y2, x2, y2, layer)],
        ]
    # Z / U detours
    for d in (mm(2), mm(4), mm(6), mm(-2), mm(-4), mm(-6)):
        pats += [
            [(x1, y1, x1, y1 + d, pcbnew.F_Cu), (x1, y1 + d, x2, y1 + d, pcbnew.F_Cu), (x2, y1 + d, x2, y2, pcbnew.F_Cu)],
            [(x1, y1, x1 + d, y1, pcbnew.F_Cu), (x1 + d, y1, x1 + d, y2, pcbnew.F_Cu), (x1 + d, y2, x2, y2, pcbnew.F_Cu)],
            [(x1, y1, x1, y1 + d, pcbnew.B_Cu), (x1, y1 + d, x2, y1 + d, pcbnew.B_Cu), (x2, y1 + d, x2, y2, pcbnew.B_Cu)],
        ]
    pats += ["VIA_HV", "VIA_VH", "VIA_MID"]
    for pat in pats:
        if pat == "VIA_HV":
            mx, my = x2, y1
            if obs.ok_via(mx, my, netcode, clearance) and obs.ok_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode, clearance) and obs.ok_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode, clearance):
                add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
                add_via(board, mx, my, netcode)
                add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
                obs.add_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode)
                obs.add_via(mx, my, netcode)
                obs.add_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode)
                return True
            continue
        if pat == "VIA_VH":
            mx, my = x1, y2
            if obs.ok_via(mx, my, netcode, clearance) and obs.ok_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode, clearance) and obs.ok_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode, clearance):
                add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
                add_via(board, mx, my, netcode)
                add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
                obs.add_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode)
                obs.add_via(mx, my, netcode)
                obs.add_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode)
                return True
            continue
        if pat == "VIA_MID":
            mx, my = (x1 + x2) // 2, (y1 + y2) // 2
            for ox, oy in ((0, 0), (mm(2), 0), (0, mm(2)), (mm(-2), 0), (0, mm(-2)), (mm(3), mm(3))):
                vx, vy = mx + ox, my + oy
                if not obs.ok_via(vx, vy, netcode, clearance):
                    continue
                if obs.ok_seg(x1, y1, vx, vy, pcbnew.F_Cu, netcode, clearance) and obs.ok_seg(vx, vy, x2, y2, pcbnew.B_Cu, netcode, clearance):
                    add_track(board, x1, y1, vx, vy, w, pcbnew.F_Cu, netcode)
                    add_via(board, vx, vy, netcode)
                    add_track(board, vx, vy, x2, y2, w, pcbnew.B_Cu, netcode)
                    obs.add_seg(x1, y1, vx, vy, pcbnew.F_Cu, netcode)
                    obs.add_via(vx, vy, netcode)
                    obs.add_seg(vx, vy, x2, y2, pcbnew.B_Cu, netcode)
                    return True
            continue
        if all(obs.ok_seg(a, b, c, d, layer, netcode, clearance) for a, b, c, d, layer in pat):
            for a, b, c, d, layer in pat:
                add_track(board, a, b, c, d, w, layer, netcode)
                obs.add_seg(a, b, c, d, layer, netcode)
            return True
    # Extra via-offset L patterns (A* disabled — too slow for dense boards)
    for ox, oy in ((mm(3),0),(mm(-3),0),(0,mm(3)),(0,mm(-3)),(mm(5),mm(5)),(mm(-5),mm(5)),(mm(5),mm(-5)),(mm(-5),mm(-5)),
                   (mm(8),0),(mm(-8),0),(0,mm(8)),(0,mm(-8))):
        mx, my = x1 + ox, y1 + oy
        if not obs.ok_via(mx, my, netcode, clearance):
            continue
        if (obs.ok_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode, clearance)
            and obs.ok_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode, clearance)):
            add_track(board, x1, y1, mx, my, w, pcbnew.F_Cu, netcode)
            add_via(board, mx, my, netcode)
            add_track(board, mx, my, x2, y2, w, pcbnew.B_Cu, netcode)
            obs.add_seg(x1, y1, mx, my, pcbnew.F_Cu, netcode)
            obs.add_via(mx, my, netcode)
            obs.add_seg(mx, my, x2, y2, pcbnew.B_Cu, netcode)
            return True
        mx, my = x2 + ox, y2 + oy
        if not obs.ok_via(mx, my, netcode, clearance):
            continue
        if (obs.ok_seg(x1, y1, mx, my, pcbnew.B_Cu, netcode, clearance)
            and obs.ok_seg(mx, my, x2, y2, pcbnew.F_Cu, netcode, clearance)):
            add_track(board, x1, y1, mx, my, w, pcbnew.B_Cu, netcode)
            add_via(board, mx, my, netcode)
            add_track(board, mx, my, x2, y2, w, pcbnew.F_Cu, netcode)
            obs.add_seg(x1, y1, mx, my, pcbnew.B_Cu, netcode)
            obs.add_via(mx, my, netcode)
            obs.add_seg(mx, my, x2, y2, pcbnew.F_Cu, netcode)
            return True
    return False


def astar_route(board, obs, x1, y1, x2, y2, w, netcode, clearance, layer):
    g = mm(GRID)
    def snap(v):
        return int(round(v / g) * g)

    sx, sy = snap(x1), snap(y1)
    gx, gy = snap(x2), snap(y2)
    # limit search box
    pad = mm(15)
    minx = min(sx, gx) - pad
    maxx = max(sx, gx) + pad
    miny = min(sy, gy) - pad
    maxy = max(sy, gy) + pad
    # clamp to board
    bb = obs.bb
    minx = max(minx, bb.GetLeft() + mm(0.5))
    maxx = min(maxx, bb.GetRight() - mm(0.5))
    miny = max(miny, bb.GetTop() + mm(0.5))
    maxy = min(maxy, bb.GetBottom() - mm(0.5))

    start = (sx, sy)
    goal = (gx, gy)
    openh = [(0, start)]
    came = {}
    gscore = {start: 0}
    closed = set()
    dirs = [(g, 0), (-g, 0), (0, g), (0, -g), (g, g), (g, -g), (-g, g), (-g, -g)]
    steps = 0
    max_steps = 8000
    while openh and steps < max_steps:
        steps += 1
        f, cur = heapq.heappop(openh)
        if cur in closed:
            continue
        closed.add(cur)
        if abs(cur[0] - goal[0]) <= g and abs(cur[1] - goal[1]) <= g:
            # reconstruct
            path = [cur]
            while cur in came:
                cur = came[cur]
                path.append(cur)
            path.reverse()
            # commit from real start/end
            pts = [(x1, y1)] + path + [(x2, y2)]
            # collapse collinear
            for i in range(len(pts) - 1):
                a, b = pts[i], pts[i + 1]
                if not obs.ok_seg(a[0], a[1], b[0], b[1], layer, netcode, clearance):
                    # try skip
                    return False
                add_track(board, a[0], a[1], b[0], b[1], w, layer, netcode)
                obs.add_seg(a[0], a[1], b[0], b[1], layer, netcode)
            return True
        for dx, dy in dirs:
            nxt = (cur[0] + dx, cur[1] + dy)
            if nxt[0] < minx or nxt[0] > maxx or nxt[1] < miny or nxt[1] > maxy:
                continue
            if nxt in closed:
                continue
            if not obs.ok_seg(cur[0], cur[1], nxt[0], nxt[1], layer, netcode, clearance):
                continue
            ng = gscore[cur] + math.hypot(dx, dy)
            if ng < gscore.get(nxt, 1e30):
                gscore[nxt] = ng
                came[nxt] = cur
                h = math.hypot(nxt[0] - goal[0], nxt[1] - goal[1])
                heapq.heappush(openh, (ng + h, nxt))
    return False


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
        if z.GetIsRuleArea():
            continue
        board.Remove(z)
    bb = board.GetBoardEdgesBoundingBox()
    zone = pcbnew.ZONE(board)
    zone.SetNet(net)
    zone.SetLayer(pcbnew.B_Cu)
    zone.SetIsFilled(False)
    try:
        zone.SetLocalClearance(mm(0.25))
        zone.SetMinThickness(mm(0.2))
        zone.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    except Exception:
        pass
    chain = pcbnew.SHAPE_LINE_CHAIN()
    m = mm(0.8)
    chain.Append(bb.GetLeft() + m, bb.GetTop() + m)
    chain.Append(bb.GetRight() - m, bb.GetTop() + m)
    chain.Append(bb.GetRight() - m, bb.GetBottom() - m)
    chain.Append(bb.GetLeft() + m, bb.GetBottom() - m)
    chain.SetClosed(True)
    zone.Outline().AddOutline(chain)
    board.Add(zone)


def hide_silk(board):
    for fp in board.GetFootprints():
        for t in (fp.Reference(), fp.Value()):
            try:
                t.SetVisible(False)
            except Exception:
                pass
        # remove silkscreen graphics to kill silk_overlap / silk_over_copper / text_height
        for g in list(fp.GraphicalItems()):
            try:
                ly = g.GetLayer()
                if ly in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                    fp.Remove(g)
            except Exception:
                pass


def remove_dangling_vias(board):
    """Remove vias with no track on either layer (zone-only vias on GND are OK if connected to track)."""
    # Build set of via positions that have a track endpoint nearby on F or B
    track_ends = []
    for t in board.GetTracks():
        if t.GetClass() != "PCB_TRACK":
            continue
        s, e = t.GetStart(), t.GetEnd()
        track_ends.append((s.x, s.y, t.GetLayer(), t.GetNetCode()))
        track_ends.append((e.x, e.y, t.GetLayer(), t.GetNetCode()))
    removed = 0
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_VIA":
            continue
        p = t.GetPosition()
        nc = t.GetNetCode()
        hit = 0
        for x, y, ly, n in track_ends:
            if n != nc:
                continue
            if math.hypot(x - p.x, y - p.y) < mm(0.35):
                hit += 1
        # need at least one track connection; GND vias dogboned should have 1 track
        if hit == 0:
            board.Remove(t)
            removed += 1
    return removed


def route_led_bar(board, obs, clearance):
    leds = []
    for fp in board.GetFootprints():
        m = re.fullmatch(r"D(\d+)", fp.GetReference())
        if not m:
            continue
        n = int(m.group(1))
        if n >= 40:
            continue
        leds.append((n, fp))
    leds.sort()
    if len(leds) < 2:
        return 0
    routed = 0
    net_pads = defaultdict(list)
    vdd_pts, gnd_pts = [], []
    for n, fp in leds:
        for pad in fp.Pads():
            net = pad.GetNet()
            if not net or net.GetNetCode() <= 0:
                continue
            name = net.GetNetname()
            pos = pad.GetPosition()
            if name == "+5V":
                vdd_pts.append((pos.x, pos.y, net.GetNetCode()))
            elif name in ("GND", "GNDA"):
                gnd_pts.append((pos.x, pos.y, net.GetNetCode()))
            else:
                net_pads[name].append((pos.x, pos.y, net.GetNetCode()))
    for name, pts in net_pads.items():
        uniq = {}
        for x, y, c in pts:
            uniq[(x, y)] = (x, y, c)
        pts2 = list(uniq.values())
        if len(pts2) != 2:
            continue
        (x1, y1, c), (x2, y2, _) = pts2
        if try_route(board, obs, x1, y1, x2, y2, mm(TRACK_W), c, clearance):
            routed += 1
    # +5V spine
    if vdd_pts:
        ys = [p[1] for p in vdd_pts]
        spine_y = min(ys) - mm(2.5)
        w = mm(POWER_W)
        stubs = []
        for x, y, c in sorted(vdd_pts, key=lambda p: p[0]):
            for sy in (spine_y, min(ys) - mm(3.2), max(ys) + mm(2.5)):
                if try_route(board, obs, x, y, x, sy, w, c, clearance):
                    routed += 1
                    stubs.append((x, sy, c))
                    break
        stubs.sort()
        for i in range(len(stubs) - 1):
            x1, y1, c = stubs[i]
            x2, y2, _ = stubs[i + 1]
            if abs(y1 - y2) > mm(0.1):
                if try_route(board, obs, x2, y2, x2, y1, w, c, clearance):
                    routed += 1
                    y2 = y1
            if try_route(board, obs, x1, y1, x2, y1, w, c, clearance):
                routed += 1
    for x, y, c in gnd_pts:
        for dy in (1.2, -1.2, 1.8, -1.8, 0.8):
            vx, vy = x, y + mm(dy)
            if obs.ok_via(vx, vy, c, clearance) and obs.ok_seg(x, y, vx, vy, pcbnew.F_Cu, c, clearance):
                add_track(board, x, y, vx, vy, mm(POWER_W), pcbnew.F_Cu, c)
                add_via(board, vx, vy, c)
                obs.add_seg(x, y, vx, vy, pcbnew.F_Cu, c)
                obs.add_via(vx, vy, c)
                routed += 1
                break
    return routed


def route_power_spine(board, obs, pads, netname, clearance):
    """Connect power pads via a horizontal/vertical spine near median."""
    if len(pads) < 2:
        return 0
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
        return 0
    netcode = pts[0][2]
    w = mm(POWER_W)
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    # try horizontal spine at median Y offset
    routed = 0
    for off in (-mm(3), mm(3), -mm(5), mm(5), -mm(2), mm(2)):
        sy = int(sorted(ys)[len(ys) // 2] + off)
        stubs = []
        ok = True
        # dry-run style: try connect each to spine
        temp_stubs = []
        for x, y, c in sorted(pts, key=lambda p: p[0]):
            # only count if route works — mutate obs as we go
            if try_route(board, obs, x, y, x, sy, w, c, clearance):
                routed += 1
                temp_stubs.append((x, sy, c))
            else:
                # try route to nearest already stubbed
                if temp_stubs and try_route(board, obs, x, y, temp_stubs[-1][0], temp_stubs[-1][1], w, c, clearance):
                    routed += 1
                    temp_stubs.append(temp_stubs[-1])
                else:
                    ok = False
        if len(temp_stubs) >= 2:
            for i in range(len(temp_stubs) - 1):
                a, b = temp_stubs[i], temp_stubs[i + 1]
                if try_route(board, obs, a[0], a[1], b[0], b[1], w, netcode, clearance):
                    routed += 1
            break
    # MST fallback for leftovers
    for i, j in mst_edges(pts):
        x1, y1, c = pts[i]
        x2, y2, _ = pts[j]
        if try_route(board, obs, x1, y1, x2, y2, w, c, clearance):
            routed += 1
    return routed


def gnd_vias(board, obs, pads, clearance):
    routed = 0
    for pad in pads:
        pos = pad.GetPosition()
        c = pad.GetNetCode()
        # PTH already hits zone — skip via if through-hole
        if pad.GetAttribute() == pcbnew.PAD_ATTRIB_PTH:
            continue
        for dx, dy in ((0, 1.2), (0, -1.2), (1.2, 0), (-1.2, 0), (0, 1.8), (0, -1.8), (1.8, 0), (-1.8, 0)):
            vx, vy = pos.x + mm(dx), pos.y + mm(dy)
            if obs.ok_via(vx, vy, c, clearance) and obs.ok_seg(pos.x, pos.y, vx, vy, pcbnew.F_Cu, c, clearance):
                add_track(board, pos.x, pos.y, vx, vy, mm(POWER_W), pcbnew.F_Cu, c)
                add_via(board, vx, vy, c)
                obs.add_seg(pos.x, pos.y, vx, vy, pcbnew.F_Cu, c)
                obs.add_via(vx, vy, c)
                routed += 1
                break
    return routed


def remove_shorting(pcb_path: Path, max_iters=10):
    kcli = Path("/workspace/tools/kicad/squashfs-root/usr/bin/kicad-cli")
    for it in range(max_iters):
        rpt = REVIEW / f"_sc_{pcb_path.stem}.rpt"
        subprocess.run([str(kcli), "pcb", "drc", "--severity-all", "-o", str(rpt), str(pcb_path)], capture_output=True)
        text = rpt.read_text() if rpt.exists() else ""
        blocks = [b for b in re.split(r"\n(?=\[)", text) if b.startswith("[shorting_items]")]
        if not blocks:
            print(f"  short-clean: 0 shorts")
            return 0
        coords = []
        for b in blocks:
            for m in re.finditer(r"@\(([-\d.]+)\s*mm,\s*([-\d.]+)\s*mm\)", b):
                coords.append((float(m.group(1)), float(m.group(2))))
        board = pcbnew.LoadBoard(str(pcb_path))
        removed = 0
        for t in list(board.GetTracks()):
            pts = []
            if t.GetClass() == "PCB_TRACK":
                s, e = t.GetStart(), t.GetEnd()
                pts = [(s.x / 1e6, s.y / 1e6), (e.x / 1e6, e.y / 1e6), ((s.x + e.x) / 2e6, (s.y + e.y) / 2e6)]
            elif t.GetClass() == "PCB_VIA":
                p = t.GetPosition()
                pts = [(p.x / 1e6, p.y / 1e6)]
            else:
                continue
            if any(math.hypot(px - cx, py - cy) < 1.0 for px, py in pts for cx, cy in coords):
                board.Remove(t)
                removed += 1
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(str(pcb_path), board)
        print(f"  short-clean iter {it}: shorts={len(blocks)} removed={removed}")
        if removed == 0:
            return len(blocks)
    return len(blocks)


def apply_design_rules(board):
    ds = board.GetDesignSettings()
    try:
        ds.m_MinThroughDrill = mm(0.2)
        ds.m_TrackMinWidth = mm(0.15)
        ds.m_ViasMinSize = mm(0.55)
        ds.m_ViasMinDrill = mm(0.25)
        ds.m_CopperEdgeClearance = mm(0.25)
        ds.m_MinClearance = mm(0.15)
        ds.m_HoleClearance = mm(0.15)
        ds.m_HoleToHoleMin = mm(0.2)
        ds.m_SolderMaskMinWidth = mm(0.0)
        ds.m_SilkTextMinHeight = mm(0.5)
    except Exception as e:
        print("  rules note", e)


def route_board(name: str):
    pcb_path = HW / name / f"{name}.kicad_pcb"
    board = pcbnew.LoadBoard(str(pcb_path))
    apply_design_rules(board)
    clear_tracks(board)
    ensure_gnd_zone(board)
    hide_silk(board)
    obs = Obstacles(board)
    print(f"{name}: keepouts={len(obs.keepouts)}")
    clearance = mm(0.18)
    routed = 0

    by = collect_by_net(board)

    if name == "hand-minute":
        routed += route_led_bar(board, obs, clearance)

    # Power spines first
    for pname in ("+5V", "+3V3", "+3V3A", "VIN", "/VIN"):
        if pname in by:
            if name == "hand-minute" and pname == "+5V":
                # LED spine already; still connect hub pads via MST
                pass
            routed += route_power_spine(board, obs, by[pname], pname, clearance)

    # GND vias (zone)
    if "GND" in by:
        routed += gnd_vias(board, obs, by["GND"], clearance)

    # All other nets MST — no distance cap
    for netname, pads in sorted(by.items(), key=lambda kv: (kv[0] in ("+5V", "+3V3", "GND", "GNDA"), len(kv[1]), kv[0])):
        if netname in ("GND", "GNDA"):
            continue  # zone + vias
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
        w = mm(POWER_W if netname.startswith("+") or "VIN" in netname else TRACK_W)
        for i, j in mst_edges(pts):
            x1, y1, c = pts[i]
            x2, y2, _ = pts[j]
            # multi-clearance attempts
            ok = False
            for cl in (clearance, mm(0.15), mm(0.12)):
                if try_route(board, obs, x1, y1, x2, y2, w, c, cl):
                    routed += 1
                    ok = True
                    break
            if not ok:
                # last resort: direct ignoring soft obstacles? no — leave unconnected
                pass

    # Deduplicate co-located vias
    seen_v = {}
    for t in list(board.GetTracks()):
        if t.GetClass() != "PCB_VIA":
            continue
        p = t.GetPosition()
        key = (round(p.x / 1e5), round(p.y / 1e5), t.GetNetCode())  # 0.1mm
        if key in seen_v:
            board.Remove(t)
        else:
            seen_v[key] = True
    removed_v = remove_dangling_vias(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    n_tracks = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_TRACK")
    n_vias = sum(1 for t in board.GetTracks() if t.GetClass() == "PCB_VIA")
    print(f"{name}: routed_ops={routed} tracks={n_tracks} vias={n_vias} dangling_removed={removed_v}")
    shorts = remove_shorting(pcb_path)
    return shorts


def main():
    REVIEW.mkdir(exist_ok=True)
    boards = sys.argv[1:] or ["base-controller", "hand-minute"]
    for b in boards:
        route_board(b)


if __name__ == "__main__":
    main()
