#!/usr/bin/env python3
"""List nets whose copper differs between two boards: python3 -I scripts/diff_copper.py a.kicad_pcb b.kicad_pcb"""
import sys
import pcbnew

mm = pcbnew.ToMM


def load(path):
    b = pcbnew.LoadBoard(path)
    d = {}
    for t in b.GetTracks():
        s, e = t.GetStart(), t.GetEnd()
        if t.GetClass() == 'PCB_VIA':
            k = ('via', round(mm(s.x), 3), round(mm(s.y), 3), round(mm(t.GetDrill()), 3))
        else:
            a, c = sorted([(round(mm(s.x), 3), round(mm(s.y), 3)), (round(mm(e.x), 3), round(mm(e.y), 3))])
            k = ('trk', b.GetLayerName(t.GetLayer()), a, c, round(mm(t.GetWidth()), 3))
        d.setdefault(t.GetNetname(), set()).add(k)
    return d, len(list(b.Zones())), len(list(b.GetFootprints()))


a, za, fa = load(sys.argv[1])
b, zb, fb = load(sys.argv[2])
print('zones', za, zb, 'footprints', fa, fb)
for n in sorted(set(a) | set(b)):
    x, y = a.get(n, set()), b.get(n, set())
    if x != y:
        print(n, 'removed', len(x - y), 'added', len(y - x))
