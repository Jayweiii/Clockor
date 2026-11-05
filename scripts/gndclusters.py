#!/usr/bin/env python3
"""Union GND fill islands through vias/pads/tracks; print the disjoint clusters.
python3 scripts/gndclusters.py pcb"""
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
gnd = b.FindNet('GND').GetNetCode()
isl = []   # (layer, poly_set, bbox)
for z in b.Zones():
    if z.GetNetCode() != gnd:
        continue
    for lyr in z.GetLayerSet().Seq():
        fp = z.GetFilledPolysList(lyr)
        for i in range(fp.OutlineCount()):
            s = pcbnew.SHAPE_POLY_SET()
            s.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)):
                s.AddHole(fp.Hole(i, h))
            isl.append((lyr, s, fp.Outline(i).BBox()))
par = list(range(len(isl)))


def find(a):
    while par[a] != a:
        par[a] = par[par[a]]
        a = par[a]
    return a


def at(lyr, pos):
    return [k for k, (l, s, bb) in enumerate(isl) if l == lyr and bb.Contains(pos) and s.Contains(pos)]


def union(ids):
    for a in ids[1:]:
        par[find(a)] = find(ids[0])


for t in b.GetTracks():
    if t.GetNetCode() != gnd:
        continue
    if t.GetClass() == 'PCB_VIA':
        union(at(pcbnew.F_Cu, t.GetPosition()) + at(pcbnew.B_Cu, t.GetPosition()))
    else:
        lyr = t.GetLayer()
        union(at(lyr, t.GetStart()) + at(lyr, t.GetEnd()))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() == gnd:
            ids = []
            for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                if p.IsOnLayer(l):
                    ids += at(l, p.GetPosition())
            union(ids)
comp = {}
for k, (l, s, bb) in enumerate(isl):
    comp.setdefault(find(k), []).append(k)
print('clusters:', len(comp))
for r, ks in sorted(comp.items(), key=lambda kv: -len(kv[1])):
    area = sum(isl[k][2].GetWidth() * isl[k][2].GetHeight() for k in ks) / 1e12
    print(len(ks), 'islands, bbox-area %.1f mm2' % area, [(b.GetLayerName(isl[k][0]), round(mm(isl[k][2].GetX()), 1), round(mm(isl[k][2].GetY()), 1)) for k in ks[:3]])
