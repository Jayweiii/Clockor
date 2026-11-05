#!/usr/bin/env python3
"""Print pads/tracks near (x, y) within +-r mm: python3 scripts/near.py x y r [pcb]"""
import sys
import pcbnew

pcb = sys.argv[4] if len(sys.argv) > 4 else 'hardware/base-controller/base-controller.kicad_pcb'
b = pcbnew.LoadBoard(pcb)
mm = pcbnew.ToMM
x, y, r = float(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3])
for fp in b.GetFootprints():
    for p in fp.Pads():
        bb = p.GetBoundingBox()
        cx, cy = mm(bb.GetCenter().x), mm(bb.GetCenter().y)
        if abs(cx - x) < r and abs(cy - y) < r:
            print('PAD', fp.GetReference(), p.GetNumber(), p.GetNetname(), round(cx, 3), round(cy, 3),
                  round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2))
for t in b.GetTracks():
    s, e = t.GetStart(), t.GetEnd()
    if min(abs(mm(s.x) - x), abs(mm(e.x) - x)) < r and min(abs(mm(s.y) - y), abs(mm(e.y) - y)) < r:
        print(t.GetClass(), t.GetNetname(), b.GetLayerName(t.GetLayer()),
              round(mm(s.x), 3), round(mm(s.y), 3), round(mm(e.x), 3), round(mm(e.y), 3), round(mm(t.GetWidth()), 2))
