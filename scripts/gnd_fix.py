#!/usr/bin/env python3
"""Surgical GND-cluster fix for the base board (does NOT re-route the board).

Reuses the grid/A* machinery of route_base.py but keeps all existing copper:
  1. rips /M1_IN1 between the B.Cu run at (100,52) and the U5.27 stub via at (114.7,44.5),
  2. links every isolated GND fill cluster to the main pour with a GND track + via,
  3. re-routes /M1_IN1 around the new GND copper,
  4. refills and re-checks the clusters.
python3 scripts/gnd_fix.py [in.kicad_pcb] [out.kicad_pcb]
"""
import sys

src = open('scripts/route_base.py').read()
i_head = src.index('result = run()')
i_write = src.index('# ---------------------------------------------------------------- write board')
i_conn = src.index('def connect_clusters')
head, mid = src[:i_head], src[i_write:i_conn]
head = head.replace('prep_pads()\nFIXED_T', 'load_existing()\nFIXED_T', 1)
LOADER = '''
def load_existing():
    for t in _keep:
        if t.GetClass() not in ('PCB_TRACK', 'PCB_VIA'):
            continue
        if t.GetClass() == 'PCB_VIA':
            try:
                dia = mm(t.GetWidth())
            except TypeError:
                dia = mm(t.GetWidth(pcbnew.F_Cu))
            vias_out.append((mm(t.GetPosition().x), mm(t.GetPosition().y), dia, mm(t.GetDrill()), t.GetNetCode()))
        else:
            s, e = t.GetStart(), t.GetEnd()
            tracks_out.append((F if t.GetLayer() == pcbnew.F_Cu else B, (mm(s.x), mm(s.y)), (mm(e.x), mm(e.y)),
                               mm(t.GetWidth()), t.GetNetCode()))
    for layer, p, q, w, net in tracks_out:
        stamp_seg(layer, p, q, w, net)
    for x, y, dia, drill, net in vias_out:
        stamp_hole(x, y, drill / 2)
        for l in (F, B):
            stamp_disc(l, x, y, dia / 2, net)

'''
head = head.replace('base_owner = [o.copy() for o in owner]', 'base_owner = [o.copy() for o in owner]\nbase_hole = holeblk.copy()', 1) if False else head
head = head.replace('base_owner = [o.copy() for o in owner]', LOADER + 'base_owner = [o.copy() for o in owner]', 1)
exec(compile(head, 'route_base(head)', 'exec'), globals())

exec(compile(mid, 'route_base(mid)', 'exec'), globals())
exec(compile(src[src.index('def gnd_clusters'):i_conn], 'route_base(clusters)', 'exec'), globals())
fill()
cl0 = gnd_clusters()
print('initial GND clusters:', len(cl0), flush=True)
IN1 = [c for c, n in nets.items() if n == '/M1_IN1'][0]
# ---- 1. rip IN1 in the congested region
keep_t, rip_t = [], []
for tr in tracks_out:
    layer, p, q, w, net = tr
    if net == IN1 and min(p[0], q[0]) >= 99.95 and not (layer == F and min(p[0], q[0]) >= 112.8):
        rip_t.append(tr)
    else:
        keep_t.append(tr)
tracks_out[:] = keep_t
vias_out[:] = [v for v in vias_out if not (v[4] == IN1 and (abs(v[0] - 102.8) < .05 or abs(v[0] - 100.2) < .05))]
print('ripped IN1 segments:', len(rip_t), flush=True)
rebuild()
sync_board()



goals = {(l, cell(y), cell(x)) for kind, x, y, ls in cl0[0] for l in ls}


def link(minor, avoid=None):
    srcs = [(l, cell(y), cell(x)) for kind, x, y, ls in minor for l in ls]
    sx = sum(s_[2] for s_ in srcs) / len(srcs)
    sy = sum(s_[1] for s_ in srcs) / len(srcs)
    gl = {q for q in goals if not avoid or math.hypot(q[2] * G - avoid[0], q[1] * G - avoid[1]) > avoid[2]}
    g = min(gl, key=lambda q: abs(q[2] - sx) + abs(q[1] - sy))
    blk = [blocked(l, GND, 0.25) for l in (F, B)]
    if avoid:
        for l in (F, B):
            blk[l] |= (X - avoid[0]) ** 2 + (Y - avoid[1]) ** 2 <= avoid[2] ** 2
    for l, r, c in srcs:
        blk[l][r, c] = False
    vblk = via_blocked(GND, VIA_SMALL[0], 0.1)
    if avoid:
        vblk = vblk | ((X - avoid[0]) ** 2 + (Y - avoid[1]) ** 2 <= avoid[2] ** 2)
    path = None
    for margin in (15, 40, 120):
        path = astar(srcs, lambda l, r, c: (l, r, c) in gl, (g[1], g[2], g[1], g[2]), blk, vblk, 6, margin)
        if path:
            break
    if not path:
        print('no GND link for cluster of %d items' % len(minor), flush=True)
        return False
    print('   path', [(('F', 'B')[l], round(c * G, 1), round(r * G, 1)) for l, r, c in path][::8])
    emit_path(path, GND, 0.25, 0.25, np.zeros((NR, NC), bool), VIA_SMALL)
    print('  linked cluster of %d items, path %d cells' % (len(minor), len(path)), flush=True)
    return True


def route_in1():
    blk = [blocked(l, IN1, 0.25) for l in (F, B)]
    vblk = via_blocked(IN1, VIA_SMALL[0])
    s_cell = (B, cell(52.0), cell(100.0))
    t_r, t_c = cell(44.5), cell(114.7)
    path = None
    for margin in (15, 40, 120, 400):
        path = astar([s_cell], lambda l, r, c: r == t_r and c == t_c, (t_r, t_c, t_r, t_c), blk, vblk, 15, margin)
        if path:
            break
    if not path:
        print('IN1 re-route FAILED', flush=True)
        return False
    emit_path(path, IN1, 0.25, 0.25, np.zeros((NR, NC), bool), VIA_SMALL)
    return True


AV = tuple(float(v) for v in sys.argv[3].split(',')) if len(sys.argv) > 3 else (114.7, 44.5, 2.0)


def rip_window(code, box):
    """Rip segments/vias of one net touching box=(x0,y0,x1,y1); keep stub tracks that start at a pad."""
    padpts = [(d.cx, d.cy) for d in by_net.get(code, [])]
    inbox = lambda p: box[0] <= p[0] <= box[2] and box[1] <= p[1] <= box[3]
    atpad = lambda p: any(abs(p[0] - x) < 0.02 and abs(p[1] - y) < 0.02 for x, y in padpts)
    n0 = len(tracks_out) + len(vias_out)
    tracks_out[:] = [t for t in tracks_out if not (t[4] == code and (inbox(t[1]) or inbox(t[2])) and not atpad(t[1]) and not atpad(t[2]))]
    vias_out[:] = [v for v in vias_out if not (v[4] == code and inbox((v[0], v[1])))]
    return n0 - len(tracks_out) - len(vias_out)


def reconnect(code):
    """Re-join the components of a net with A* (0.2 mm tracks)."""
    nodes = []          # (kind, key, cells)
    for d in by_net.get(code, []):
        if d.skip:
            continue
        nodes.append(('pad', (d.cx, d.cy), None, d))
    ends = []
    for layer, p, q, w, net in tracks_out:
        if net == code:
            ends.append((layer, p, q))
    # union-find over points
    pts = {}

    def key(pt):
        return (round(pt[0], 2), round(pt[1], 2))
    par = {}

    def find(a):
        par.setdefault(a, a)
        while par[a] != a:
            par[a] = par[par[a]]
            a = par[a]
        return a

    def un(a, b):
        par[find(a)] = find(b)
    for layer, p, q, in [(e[0], e[1], e[2]) for e in ends]:
        un(('t', key(p)), ('t', key(q)))
    for v in vias_out:
        if v[4] == code:
            un(('t', key((v[0], v[1]))), ('t', key((v[0], v[1]))))
    # tie track endpoints at the same position (any layer joined only through vias)
    vpos = {key((v[0], v[1])) for v in vias_out if v[4] == code}
    # layer-aware nodes: (layer, key)
    par.clear()
    for layer, p, q in ends:
        un((layer, key(p)), (layer, key(q)))
    for k in vpos:
        un((F, k), (B, k))
    # pads: join any endpoint inside the pad on a pad layer
    padnode = {}
    for kind, kk, _, d in nodes:
        pn = ('pad', id(d))
        padnode[pn] = d
        find(pn)
        for layer, p, q in ends:
            for pt in (p, q):
                if layer in d.layers and d.x0 - 0.02 <= pt[0] <= d.x1 + 0.02 and d.y0 - 0.02 <= pt[1] <= d.y1 + 0.02:
                    un(pn, (layer, key(pt)))
    comps = {}
    for node in list(par):
        comps.setdefault(find(node), []).append(node)
    comps = list(comps.values())
    if len(comps) <= 1:
        return True

    def cells_of(comp):
        out = []
        for nd in comp:
            if nd[0] == 'pad':
                d = padnode[nd]
                blk0 = [blocked(l, code, 0.2) for l in (F, B)]
                out += pad_cells(d, blk0)
            else:
                layer, k = nd
                out.append((layer, cell(k[1]), cell(k[0])))
        return out
    base = max(comps, key=len)
    comps.remove(base)
    tree = cells_of(base)
    for comp in comps:
        goalc = set(cells_of(comp))
        if not goalc:
            return False
        blk = [blocked(l, code, 0.2) for l in (F, B)]
        vblk = via_blocked(code, VIA_SMALL[0])
        rs = [t[1] for t in goalc]
        cs = [t[2] for t in goalc]
        path = None
        for margin in (10, 25, 80):
            path = astar(tree, lambda l, r, c: (l, r, c) in goalc, (min(rs), min(cs), max(rs), max(cs)), blk, vblk, 15, margin)
            if path:
                break
        if not path:
            return False
        emit_path(path, code, 0.2, 0.2, np.zeros((NR, NC), bool), VIA_SMALL)
        tree += list(goalc) + path
    return True


def segdist(pt, a, b):
    dx, dy = b[0] - a[0], b[1] - a[1]
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((pt[0] - a[0]) * dx + (pt[1] - a[1]) * dy) / L2))
    return math.hypot(a[0] + t * dx - pt[0], a[1] + t * dy - pt[1])


def fix_dangling(code):
    """Truncate stubs that overshoot a via, prune spurs that end in nothing."""
    changed = True
    while changed:
        changed = False
        pds = by_net.get(code, [])
        vs = [v for v in vias_out if v[4] == code]
        for i, (layer, p, q, w, net) in enumerate(tracks_out):
            if net != code:
                continue
            for end, other in ((q, p), (p, q)):
                touch = any(j != i and t[4] == code and t[0] == layer and segdist(end, t[1], t[2]) < 0.02
                            for j, t in enumerate(tracks_out))
                touch = touch or any(math.hypot(v[0] - end[0], v[1] - end[1]) <= v[2] / 2 for v in vs)
                touch = touch or any(layer in d.layers and d.x0 - 0.02 <= end[0] <= d.x1 + 0.02 and d.y0 - 0.02 <= end[1] <= d.y1 + 0.02 for d in pds)
                if touch:
                    continue
                # overshoot: a via of this net that the segment passes through
                dx, dy = end[0] - other[0], end[1] - other[1]
                L2 = dx * dx + dy * dy
                best = None
                for v in vs:
                    t_ = ((v[0] - other[0]) * dx + (v[1] - other[1]) * dy) / L2 if L2 else 0
                    if 0 < t_ < 1:
                        pr = (other[0] + t_ * dx, other[1] + t_ * dy)
                        if math.hypot(pr[0] - v[0], pr[1] - v[1]) <= v[2] / 2 - 0.1 and (best is None or t_ < best[0]):
                            best = (t_, pr)
                if best:
                    tracks_out[i] = (layer, other, best[1], w, net) if end is q else (layer, best[1], other, w, net)
                else:
                    del tracks_out[i]
                changed = True
                break
            if changed:
                break
    rebuild()


def snapshot():
    return (list(tracks_out), list(vias_out))


def restore_snap(st):
    tracks_out[:] = st[0]
    vias_out[:] = st[1]
    rebuild()


import itertools
byname = {n: c for c, n in nets.items()}
ok = link(cl0[1]) and route_in1()
print('stage1 ok', ok, flush=True)
if ok:
    done = False
    cands = ['/M1_EN1', '/M1_IN3', '/M1_IN2', '/M1_nFAULT', '/M1_IN1']
    box = (110.0, 42.0, 116.0, 50.5)
    for k in (1, 2, 3):
        for combo in itertools.combinations(cands, k):
            st = snapshot()
            nr = sum(rip_window(byname[n], box) for n in combo)
            rebuild()
            if link(cl0[2]):
                good = all(reconnect(byname[n]) for n in combo)
                for n in combo:
                    fix_dangling(byname[n])
                print('combo', combo, 'ripped', nr, 'reconnect', good, flush=True)
                if good:
                    sync_board()
                    fill()
                    cl = gnd_clusters()
                    print('clusters after combo:', len(cl), flush=True)
                    if len(cl) == 1:
                        done = True
                        break
            restore_snap(st)
        if done:
            break
    ok = done
sync_board()
fill()
cl = gnd_clusters()
print('ok', ok, 'final GND clusters:', len(cl))
if ok and len(cl) == 1:
    pcbnew.SaveBoard(DST, board)
    print('saved', DST)
