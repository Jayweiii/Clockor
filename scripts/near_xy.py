"""List tracks near a point: near_xy.py board x0 x1 y0 y1"""
import pcbnew, sys
b = pcbnew.LoadBoard(sys.argv[1]); mm = pcbnew.ToMM
x0, x1, y0, y1 = map(float, sys.argv[2:6])
for t in b.GetTracks():
    if t.GetClass() != 'PCB_VIA' and x0 < mm(t.GetStart().x) < x1 and y0 < mm(t.GetStart().y) < y1:
        print(t.GetNetname(), b.GetLayerName(t.GetLayer()), round(mm(t.GetStart().x), 3), round(mm(t.GetStart().y), 3),
              round(mm(t.GetEnd().x), 3), round(mm(t.GetEnd().y), 3), mm(t.GetWidth()))
