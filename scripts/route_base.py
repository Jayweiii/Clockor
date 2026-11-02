#!/usr/bin/env python3
"""Two-layer grid router for the base board (v0.5).

Run inside the KiCad container:  python3 scripts/route_base.py [in.kicad_pcb] [out.kicad_pcb]

Strips all tracks/vias/zones, then
  1. places pin-escape stubs on fine-pitch pads (straight out of the pad, off-grid),
  2. routes nets on a 0.1 mm grid with per-net trunk widths and a narrower "neck"
     near fine-pitch pins (A*, 8-neighbour, vias allowed),
  3. ties every GND pad to the GND pours with a short stub + via,
  4. adds GND pours on F.Cu and B.Cu with ~5 mm stitching vias and fills them.
Schematic, footprints and outline are never touched.
"""
import heapq
import math
import sys
import pcbnew
import numpy as np

SRC = sys.argv[1] if len(sys.argv) > 1 else 'hardware/base-controller/base-controller.kicad_pcb'
DST = sys.argv[2] if len(sys.argv) > 2 else SRC

G = 0.1            # grid pitch, mm
CLR = 0.1          # board min clearance
RQ = 0.04          # raster quantisation margin
EDGE = 0.35        # copper to board edge keepout (+ half width)
nm = pcbnew.FromMM
mm = pcbnew.ToMM
F, B = 0, 1
LAYER = [pcbnew.F_Cu, pcbnew.B_Cu]

# trunk widths (mm). Everything not listed is a 0.25 signal.
WIDTH = {
    '/VIN_12V': 1.5, '/BUCK_SW': 1.5, '+5V': 1.5,
    '/M1_OUTA': 1.5, '/M1_OUTB': 1.5, '/M1_OUTC': 1.5,
    '+3V3': 0.5, '/M1_V3P3': 0.5,
    '/HR_OUT1': 0.5, '/HR_OUT2': 0.5, '/HR_OUT3': 0.5, '/HR_OUT4': 0.5,
}
ORDER = ['/VIN_12V', '/BUCK_SW', '+5V', '/M1_OUTA', '/M1_OUTB', '/M1_OUTC',
         '/BUCK_FB', '+3V3', '/M1_V3P3', '/HR_OUT1', '/HR_OUT2', '/HR_OUT3', '/HR_OUT4',
         '/USB_D+', '/USB_D-']
FALLBACK = [1.5, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.25]
VIA_BIG = (0.8, 0.4)
VIA_SMALL = (0.6, 0.3)
ZONE_R = 3.0       # radius around neck pads where the narrow neck width applies


def neck_of(w):
    return 0.2 if w <= 0.25 else min(w, 0.5)


board = pcbnew.LoadBoard(SRC)
_keep = []
for t in list(board.GetTracks()):
    _keep.append(t)
    board.RemoveNative(t)
for z in list(board.Zones()):
    _keep.append(z)
    board.RemoveNative(z)

bb = board.GetBoardEdgesBoundingBox()
BX0, BY0, BX1, BY1 = mm(bb.GetLeft()), mm(bb.GetTop()), mm(bb.GetRight()), mm(bb.GetBottom())
NC = int(math.ceil(BX1 / G)) + 2
NR = int(math.ceil(BY1 / G)) + 2

owner = [np.zeros((NR, NC), np.int16) for _ in range(2)]   # raw copper owner (net code), -1 = foreign obstacle

yy, xx = np.mgrid[0:NR, 0:NC]
X = xx * G
Y = yy * G


def cell(v):
    return int(round(v / G))


def stamp_rect(layer, x0, y0, x1, y1, net, margin=0.05):
    c0 = max(0, int(math.ceil((x0 - margin) / G)))
    c1 = min(NC - 1, int(math.floor((x1 + margin) / G)))
    r0 = max(0, int(math.ceil((y0 - margin) / G)))
    r1 = min(NR - 1, int(math.floor((y1 + margin) / G)))
    if c1 < c0 or r1 < r0:
        return
    sub = owner[layer][r0:r1 + 1, c0:c1 + 1]
    sub[sub == 0] = net


def stamp_disc(layer, x, y, r, net):
    r = r + RQ
    c0 = max(0, int(math.floor((x - r) / G)))
    c1 = min(NC - 1, int(math.ceil((x + r) / G)))
    r0 = max(0, int(math.floor((y - r) / G)))
    r1 = min(NR - 1, int(math.ceil((y + r) / G)))
    sub = owner[layer][r0:r1 + 1, c0:c1 + 1]
    m = ((X[r0:r1 + 1, c0:c1 + 1] - x) ** 2 + (Y[r0:r1 + 1, c0:c1 + 1] - y) ** 2) <= r * r
    sub[m & (sub == 0)] = net


def stamp_seg(layer, p, q, w, net):
    L = math.hypot(q[0] - p[0], q[1] - p[1])
    n = max(1, int(L / 0.05))
    for i in range(n + 1):
        t = i / n
        stamp_disc(layer, p[0] + (q[0] - p[0]) * t, p[1] + (q[1] - p[1]) * t, w / 2, net)


holeblk = np.zeros((NR, NC), bool)


def stamp_hole(x, y, drill_r):
    r = drill_r + 0.15 + 0.15 + 0.1     # hole-to-hole 0.15 + new via drill radius + margin
    c0 = max(0, int(math.floor((x - r) / G)))
    c1 = min(NC - 1, int(math.ceil((x + r) / G)))
    r0 = max(0, int(math.floor((y - r) / G)))
    r1 = min(NR - 1, int(math.ceil((y + r) / G)))
    holeblk[r0:r1 + 1, c0:c1 + 1] |= ((X[r0:r1 + 1, c0:c1 + 1] - x) ** 2 + (Y[r0:r1 + 1, c0:c1 + 1] - y) ** 2) <= r * r


# ---------------------------------------------------------------- pads
class Pad:
    pass


pads = []
nets = {}          # code -> name
for fp in board.GetFootprints():
    for p in fp.Pads():
        pb = p.GetBoundingBox()
        d = Pad()
        d.ref = fp.GetReference()
        d.num = p.GetNumber()
        d.code = p.GetNetCode()
        d.name = p.GetNetname()
        d.x0, d.y0, d.x1, d.y1 = mm(pb.GetLeft()), mm(pb.GetTop()), mm(pb.GetRight()), mm(pb.GetBottom())
        d.cx, d.cy = (d.x0 + d.x1) / 2, (d.y0 + d.y1) / 2
        d.fpx, d.fpy = mm(fp.GetPosition().x), mm(fp.GetPosition().y)
        d.attr = p.GetAttribute()
        d.thru = d.attr in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH)
        d.drill = mm(max(p.GetDrillSizeX(), p.GetDrillSizeY()))
        d.layers = [l for l, ly in ((F, pcbnew.F_Cu), (B, pcbnew.B_Cu)) if p.IsOnLayer(ly)]
        d.p = p
        d.stub = None      # (end point, cell) for stub pads
        d.neck = False
        d.skip = False
        pads.append(d)
        if d.code > 0:
            nets[d.code] = d.name
        for l in d.layers:
            stamp_rect(l, d.x0, d.y0, d.x1, d.y1, d.code if d.code > 0 else -1)
        if d.thru and d.drill > 0:
            stamp_hole(d.cx, d.cy, d.drill / 2)
        if d.attr == pcbnew.PAD_ATTRIB_NPTH:
            for l in (F, B):
                stamp_disc(l, d.cx, d.cy, d.drill / 2 + 0.25, -1)
    for z in fp.Zones():           # footprint keepouts (ESP32 antenna)
        if z.GetIsRuleArea():
            kb = z.GetBoundingBox()
            for l in (F, B):
                stamp_rect(l, mm(kb.GetLeft()), mm(kb.GetTop()), mm(kb.GetRight()), mm(kb.GetBottom()), -1, 0.3)
# board edge handled in blocked()

by_net = {}
for d in pads:
    if d.code > 0:
        by_net.setdefault(d.code, []).append(d)

GND = [c for c, n in nets.items() if n == 'GND'][0]


def dilate(mask, r):
    rc = r / G
    n = int(math.floor(rc))
    if n == 0:
        return mask.copy()
    hd = [mask]
    for h in range(1, n + 1):
        prev = hd[-1]
        cur = prev.copy()
        cur[:, h:] |= mask[:, :-h]
        cur[:, :-h] |= mask[:, h:]
        hd.append(cur)
    out = mask.copy()
    for dy in range(-n, n + 1):
        hx = int(math.floor(math.sqrt(max(0.0, rc * rc - dy * dy))))
        src = hd[hx]
        if dy == 0:
            out |= src
        elif dy > 0:
            out[dy:, :] |= src[:-dy, :]
        else:
            out[:dy, :] |= src[-dy:, :]
    return out


edge_cache = {}


def edge_block(w):
    k = round(w, 3)
    if k not in edge_cache:
        m = EDGE + w / 2
        edge_cache[k] = (X < BX0 + m) | (X > BX1 - m) | (Y < BY0 + m) | (Y > BY1 - m)
    return edge_cache[k]


def other_mask(layer, net):
    o = owner[layer]
    return (o != 0) & (o != net)


def blocked(layer, net, w):
    return dilate(other_mask(layer, net), w / 2 + CLR + RQ) | edge_block(w)


def via_blocked(net, d, extra=0.0):
    m = other_mask(F, net) | other_mask(B, net)
    return dilate(m, d / 2 + CLR + RQ + extra) | edge_block(d) | holeblk


# ---------------------------------------------------------------- stubs
tracks_out = []   # (layer, p, q, w, net)
vias_out = []     # (x, y, dia, drill, net)


def add_track(layer, p, q, w, net):
    if math.hypot(q[0] - p[0], q[1] - p[1]) < 0.002:
        return
    tracks_out.append((layer, p, q, w, net))
    stamp_seg(layer, p, q, w, net)


def add_via(x, y, size, net):
    vias_out.append((x, y, size[0], size[1], net))
    stamp_hole(x, y, size[1] / 2)
    for l in (F, B):
        stamp_disc(l, x, y, size[0] / 2, net)


def net_width(code):
    return WIDTH.get(nets.get(code, ''), 0.25)


def prep_pads():
    seen = set()
    gnd_idx = {}
    for d in pads:
        if d.code <= 0 or d.thru or len(by_net.get(d.code, [])) < 2:
            continue
        w, h = d.x1 - d.x0, d.y1 - d.y0
        short, long_ = min(w, h), max(w, h)
        if short < 1.6:
            d.neck = True
        key = (round(d.x0, 2), round(d.y0, 2), round(d.x1, 2), round(d.y1, 2), d.code)
        if key in seen:
            d.skip = True        # coincident duplicate pad (USB-C A/B mirrored pins)
            continue
        seen.add(key)
        if not (short < 1.0 and long_ / short >= 1.5):
            continue
        horiz = w > h
        if horiz:
            sgn = 1 if d.cx >= d.fpx else -1
        else:
            sgn = 1 if d.cy >= d.fpy else -1
        is_gnd = d.code == GND
        # footprint-level side grouping for GND via staggering
        kk = (d.ref, horiz, sgn)
        i = gnd_idx.get(kk, 0)
        if is_gnd:
            gnd_idx[kk] = i + 1
        ls = (0.6 + 0.4 * (i % 2)) if is_gnd else 1.3
        lat = d.cy if horiz else d.cx
        sw = min(neck_of(net_width(d.code)), short) if not is_gnd else min(0.25, short)
        for attempt in (0, 1):
            if horiz:
                edge = d.x1 if sgn > 0 else d.x0
                if is_gnd:
                    end = edge + sgn * ls
                else:
                    end = (math.ceil((edge + sgn * ls) / G) if sgn > 0 else math.floor((edge + sgn * ls) / G)) * G
                ex, ey = end, lat
            else:
                edge = d.y1 if sgn > 0 else d.y0
                if is_gnd:
                    end = edge + sgn * ls
                else:
                    end = (math.ceil((edge + sgn * ls) / G) if sgn > 0 else math.floor((edge + sgn * ls) / G)) * G
                ex, ey = lat, end
            if BX0 + 1.0 < ex < BX1 - 1.0 and BY0 + 1.0 < ey < BY1 - 1.0:
                break
            sgn = -sgn
        start = (d.cx, d.cy)
        add_track(F, start, (ex, ey), sw, d.code)
        if is_gnd:
            add_via(ex, ey, VIA_SMALL, GND)
            d.skip = True        # fully handled
        else:
            if horiz:
                cx_, cy_ = ex, cell(ey) * G
            else:
                cx_, cy_ = cell(ex) * G, ey
            add_track(F, (ex, ey), (cx_, cy_), sw, d.code)
            d.stub = (cell(cy_), cell(cx_))
            d.stub_w = sw


prep_pads()

# ---------------------------------------------------------------- A*
SQ2 = math.sqrt(2)
NB = [(-1, 0, 1), (1, 0, 1), (0, -1, 1), (0, 1, 1),
      (-1, -1, SQ2), (-1, 1, SQ2), (1, -1, SQ2), (1, 1, SQ2)]


def astar(srcs, goal_fn, tbox, blk, vblk, via_cost, margin_mm, keepout=None):
    """srcs: list of (l,r,c). goal_fn(l,r,c)->bool. tbox: (r0,c0,r1,c1) cells for heuristic."""
    allr = [s[1] for s in srcs] + [tbox[0], tbox[2]]
    allc = [s[2] for s in srcs] + [tbox[1], tbox[3]]
    m = int(margin_mm / G)
    r0 = max(1, min(allr) - m)
    r1 = min(NR - 2, max(allr) + m)
    c0 = max(1, min(allc) - m)
    c1 = min(NC - 2, max(allc) + m)
    hh, ww = r1 - r0 + 1, c1 - c0 + 1
    bl = []
    for l in (F, B):
        a = blk[l][r0:r1 + 1, c0:c1 + 1].copy()
        if keepout is not None:
            a |= keepout[l][r0:r1 + 1, c0:c1 + 1]
        a[0, :] = a[-1, :] = True
        a[:, 0] = a[:, -1] = True
        bl.append(a.astype(np.uint8).ravel().tolist())
    vb = vblk[r0:r1 + 1, c0:c1 + 1].astype(np.uint8).ravel().tolist()
    N = hh * ww
    INF = 1e18
    g = [INF] * (2 * N)
    par = {}
    heap = []
    tr0, tc0, tr1, tc1 = tbox
    W_ = 1.4
    for (l, r, c) in srcs:
        r -= r0
        c -= c0
        if not (0 <= r < hh and 0 <= c < ww):
            continue
        s = l * N + r * ww + c
        g[s] = 0
        heapq.heappush(heap, (0, 0, s))
    steps = [(dr * ww + dc, cost) for dr, dc, cost in NB]
    goal = None
    while heap:
        f, gc, s = heapq.heappop(heap)
        if gc > g[s]:
            continue
        l = s // N
        rem = s - l * N
        r = rem // ww
        c = rem - r * ww
        if goal_fn(l, r + r0, c + c0):
            goal = s
            break
        base = l * N
        arr = bl[l]
        for (d, cost), (dr, dc, _) in zip(steps, NB):
            t = rem + d
            if arr[t]:
                continue
            # diagonal: avoid squeezing between two blocked orthogonals
            if dr and dc and (arr[rem + dr * ww] or arr[rem + dc]):
                continue
            ng = gc + cost
            ts = base + t
            if ng < g[ts]:
                g[ts] = ng
                par[ts] = s
                rr = t // ww + r0
                cc = t % ww + c0
                ddx = max(tc0 - cc, 0, cc - tc1)
                ddy = max(tr0 - rr, 0, rr - tr1)
                h = ddx + ddy + (SQ2 - 2) * min(ddx, ddy)
                heapq.heappush(heap, (ng + W_ * h, ng, ts))
        if not vb[rem]:
            o = 1 - l
            if not bl[o][rem]:
                ts = o * N + rem
                ng = gc + via_cost
                if ng < g[ts]:
                    g[ts] = ng
                    par[ts] = s
                    rr = r + r0
                    cc = c + c0
                    ddx = max(tc0 - cc, 0, cc - tc1)
                    ddy = max(tr0 - rr, 0, rr - tr1)
                    h = ddx + ddy + (SQ2 - 2) * min(ddx, ddy)
                    heapq.heappush(heap, (ng + W_ * h, ng, ts))
    if goal is None:
        return None
    path = []
    s = goal
    while True:
        l = s // N
        rem = s - l * N
        path.append((l, rem // ww + r0, rem % ww + c0))
        if s not in par:
            break
        s = par[s]
    path.reverse()
    return path


def zone_mask(plist):
    m = np.zeros((NR, NC), bool)
    for d in plist:
        if not d.neck:
            continue
        r0 = max(0, int((d.cy - ZONE_R) / G))
        r1 = min(NR - 1, int((d.cy + ZONE_R) / G) + 1)
        c0 = max(0, int((d.cx - ZONE_R) / G))
        c1 = min(NC - 1, int((d.cx + ZONE_R) / G) + 1)
        m[r0:r1 + 1, c0:c1 + 1] |= ((X[r0:r1 + 1, c0:c1 + 1] - d.cx) ** 2 + (Y[r0:r1 + 1, c0:c1 + 1] - d.cy) ** 2) <= ZONE_R ** 2
    return m


def pad_cells(d, blk):
    if d.stub is not None:
        r, c = d.stub
        sb = blocked(F, d.code, d.stub_w)
        return [(F, r, c)] if not sb[r, c] else []
    out = []
    c0 = int(math.ceil(d.x0 / G))
    c1 = int(math.floor(d.x1 / G))
    r0 = int(math.ceil(d.y0 / G))
    r1 = int(math.floor(d.y1 / G))
    for l in d.layers:
        for r in range(r0, r1 + 1):
            for c in range(c0, c1 + 1):
                if not blk[l][r, c] and d.p.HitTest(pcbnew.VECTOR2I(nm(c * G), nm(r * G))):
                    out.append((l, r, c))
    if not out:
        for l in d.layers:
            rr, cc = cell(d.cy), cell(d.cx)
            for r in range(rr - 2, rr + 3):
                for c in range(cc - 2, cc + 3):
                    if not blk[l][r, c] and d.p.HitTest(pcbnew.VECTOR2I(nm(c * G), nm(r * G))):
                        out.append((l, r, c))
    return out


def emit_path(path, code, wt, wn, zmask, via):
    """Turn a cell path into tracks/vias; returns the cell set of the path."""
    def width_at(l, r, c):
        return wn if zmask[r, c] else wt
    i = 0
    n = len(path)
    segs = []
    while i < n - 1:
        a, b = path[i], path[i + 1]
        if a[0] != b[0]:
            add_via(a[2] * G, a[1] * G, via, code)
            i += 1
            continue
        w = min(width_at(*a), width_at(*b))
        dr, dc = b[1] - a[1], b[2] - a[2]
        j = i + 1
        while j < n - 1:
            nxt = path[j + 1]
            if nxt[0] != a[0] or (nxt[1] - path[j][1], nxt[2] - path[j][2]) != (dr, dc):
                break
            if min(width_at(*path[j]), width_at(*nxt)) != w:
                break
            j += 1
        p = (a[2] * G, a[1] * G)
        q = (path[j][2] * G, path[j][1] * G)
        segs.append((a[0], p, q, w))
        i = j
    for l, p, q, w in segs:
        add_track(l, p, q, w, code)


def route_net(code, width, keepout_mm=None):
    plist = [d for d in by_net[code] if not d.skip]
    if len(plist) < 2:
        return True, []
    wt = width
    wn = neck_of(wt) if wt > 0.25 else 0.2
    zmask = zone_mask(plist)
    via = VIA_BIG if wt > 0.3 else VIA_SMALL
    blk = []
    for l in (F, B):
        bt = blocked(l, code, wt)
        bn = blocked(l, code, wn) if wn < wt else bt
        blk.append(np.where(zmask, bn, bt))
    vblk = via_blocked(code, via[0])
    keep = None
    if keepout_mm:
        keep = []
        for l in (F, B):
            mo = np.zeros((NR, NC), bool)
            for cc, nn in nets.items():
                if nn.startswith('/M1_OUT'):
                    mo |= owner[l] == cc
            keep.append(dilate(mo, keepout_mm))
    terms = {}
    for d in plist:
        t = pad_cells(d, blk)
        if not t:
            return False, ['no free cell at %s.%s' % (d.ref, d.num)]
        terms[id(d)] = t
    # start from the pad with the most constrained access (stub pads first), then Prim
    order = sorted(plist, key=lambda d: (d.stub is None, len(terms[id(d)])))
    tree = set(terms[id(order[0])])
    remaining = order[1:]
    log = []
    while remaining:
        best = None
        for d in remaining:
            ts = terms[id(d)]
            dist = min(abs(t[1] - s[1]) + abs(t[2] - s[2]) for t in ts[:1] for s in list(tree)[:400])
            if best is None or dist < best[0]:
                best = (dist, d)
        d = best[1]
        ts = set(terms[id(d)])
        rs = [t[1] for t in ts]
        cs = [t[2] for t in ts]
        tbox = (min(rs), min(cs), max(rs), max(cs))
        path = None
        for margin in (8, 20, 60, 200):
            path = astar(list(tree), lambda l, r, c: (l, r, c) in ts, tbox, blk, vblk,
                         25 if wt > 0.3 else 15, margin, keep)
            if path:
                break
        if path is None:
            return False, ['no path to %s.%s' % (d.ref, d.num)]
        emit_path(path, code, wt, wn, zmask, via)
        tree |= set(path)
        tree |= ts
        remaining.remove(d)
    return True, log


# ---------------------------------------------------------------- main routing
def run():
    names = {v: k for k, v in nets.items()}
    todo = []
    for code, pl in by_net.items():
        if code == GND:
            continue
        if len([d for d in pl if not d.skip]) < 2:
            continue
        todo.append(code)

    import os
    prio = [x for x in os.environ.get('PRIORITY', '/BOOT,/M1_EN1,/M1_CPH,/M1_IN1,/USB_D-').split(',') if x]

    def key(code):
        n = nets[code]
        if n in prio:
            return (0.5, prio.index(n))
        if n in ORDER:
            return (0, ORDER.index(n))
        if 'I2C' in n:
            return (2, 0)
        pl = by_net[code]
        xs = [d.cx for d in pl]
        ys = [d.cy for d in pl]
        return (1, (max(xs) - min(xs)) + (max(ys) - min(ys)))
    todo.sort(key=key)
    result = {}
    for code in todo:
        n = nets[code]
        base = net_width(code)
        ws = [w for w in FALLBACK if w <= base + 1e-9] or [base]
        done = False
        for w in ws:
            before_t, before_v = len(tracks_out), len(vias_out)
            snap = [o.copy() for o in owner]
            kos = (5.0, 2.5, None) if 'I2C' in n else (None,)
            for ko in kos:
                ok, log = route_net(code, w, ko)
                if ok:
                    break
                print('   %s w=%.2f ko=%s: %s' % (n, w, ko, log), flush=True)
                del tracks_out[before_t:]
                del vias_out[before_v:]
                for l in (F, B):
                    owner[l][:] = snap[l]
            if ok:
                result[n] = w
                print('ROUTED %-14s width %.2f' % (n, w), flush=True)
                done = True
                break
        if not done:
            result[n] = None
            print('FAILED %-14s %s' % (n, log), flush=True)
    return result


def gnd_ties():
    """Every remaining SMD GND pad gets a stub + via to the pours."""
    fails = []
    vsz = VIA_SMALL
    for d in by_net.get(GND, []):
        if d.skip or d.thru or d.stub is not None:
            continue
        w = 0.3
        blk = [blocked(l, GND, w) for l in (F, B)]
        vblk = via_blocked(GND, vsz[0], 0.1)
        ts = pad_cells(d, blk)
        if not ts:
            fails.append('%s.%s no cell' % (d.ref, d.num))
            continue
        # via-in-pad is the last resort; try near-pad via first
        tset = set(ts)
        path = None
        for margin in (5, 15):
            path = astar(ts, lambda l, r, c: l == F and not vblk[r, c] and (F, r, c) not in tset,
                         (ts[0][1], ts[0][2], ts[0][1], ts[0][2]), blk, vblk, 6, margin)
            if path:
                break
        if path is None:
            ok = [t for t in ts if t[0] == F and not vblk[t[1], t[2]]]
            if ok:
                add_via(ok[0][2] * G, ok[0][1] * G, vsz, GND)
            else:
                fails.append('%s.%s no via spot' % (d.ref, d.num))
            continue
        # stop path at the first via-ok cell (goal), drop via there
        gl, gr, gc = path[-1]
        emit_path(path, GND, w, w, np.zeros((NR, NC), bool), vsz)
        add_via(gc * G, gr * G, vsz, GND)
    return fails


def stitch():
    n = 0
    vb = via_blocked(GND, VIA_SMALL[0], 0.25)
    xs = np.arange(math.ceil((BX0 + 2) / 5.0) * 5.0, BX1 - 2, 5.0)
    ys = np.arange(math.ceil((BY0 + 2) / 5.0) * 5.0, BY1 - 2, 5.0)
    for y in ys:
        for x in xs:
            c, r = cell(x), cell(y)
            if vb[r, c]:
                continue
            if any(abs(v[0] - x) < 1.2 and abs(v[1] - y) < 1.2 for v in vias_out if v[4] == GND):
                continue
            add_via(c * G, r * G, VIA_SMALL, GND)
            n += 1
    return n


result = run()
gf = gnd_ties()
print('GND tie failures:', gf)
ns = stitch()
print('stitching vias:', ns)

# ---------------------------------------------------------------- write board
for layer, p, q, w, net in tracks_out:
    t = pcbnew.PCB_TRACK(board)
    t.SetStart(pcbnew.VECTOR2I(nm(p[0]), nm(p[1])))
    t.SetEnd(pcbnew.VECTOR2I(nm(q[0]), nm(q[1])))
    t.SetWidth(nm(w))
    t.SetLayer(LAYER[layer])
    t.SetNetCode(net)
    board.Add(t)
for x, y, dia, drill, net in vias_out:
    v = pcbnew.PCB_VIA(board)
    v.SetPosition(pcbnew.VECTOR2I(nm(x), nm(y)))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetDrill(nm(drill))
    try:
        v.SetWidth(nm(dia))
    except TypeError:
        v.SetWidth(pcbnew.F_Cu, nm(dia))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    v.SetNetCode(net)
    board.Add(v)

for lyr in LAYER:
    z = pcbnew.ZONE(board)
    z.SetLayer(lyr)
    z.SetNetCode(GND)
    z.SetMinThickness(nm(0.2))
    z.SetLocalClearance(nm(0.25))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_FULL)
    z.SetIslandRemovalMode(pcbnew.ISLAND_REMOVAL_MODE_ALWAYS)
    o = z.Outline()
    o.NewOutline()
    m = 0.3
    for px, py in ((BX0 + m, BY0 + m), (BX1 - m, BY0 + m), (BX1 - m, BY1 - m), (BX0 + m, BY1 - m)):
        o.Append(nm(px), nm(py))
    board.Add(z)
pcbnew.ZONE_FILLER(board).Fill(board.Zones())
pcbnew.SaveBoard(DST, board)
print('saved', DST)
print(result)
