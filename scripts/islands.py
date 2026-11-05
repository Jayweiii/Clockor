#!/usr/bin/env python3
"""Report GND zone islands containing no GND pad/via: python3 scripts/islands.py pcb"""
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
gnd = b.FindNet('GND').GetNetCode()
pts = []
for t in b.GetTracks():
    if t.GetNetCode() == gnd and t.GetClass() == 'PCB_VIA':
        pts.append(('via', t.GetPosition(), [pcbnew.F_Cu, pcbnew.B_Cu]))
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetCode() == gnd:
            pts.append(('pad ' + fp.GetReference() + '.' + p.GetNumber(), p.GetPosition(),
                        [l for l in (pcbnew.F_Cu, pcbnew.B_Cu) if p.IsOnLayer(l)]))
filled = {}
for z in b.Zones():
    for lyr in z.GetLayerSet().Seq():
        filled[lyr] = z.GetFilledPolysList(lyr)


def in_fill(lyr, pos):
    fp = filled[lyr]
    for i in range(fp.OutlineCount()):
        single = pcbnew.SHAPE_POLY_SET()
        single.AddOutline(fp.Outline(i))
        for h in range(fp.HoleCount(i)):
            single.AddHole(fp.Hole(i, h))
        if single.Contains(pos):
            return True
    return False


for z in b.Zones():
    for lyr in z.GetLayerSet().Seq():
        fp = z.GetFilledPolysList(lyr)
        for i in range(fp.OutlineCount()):
            single = pcbnew.SHAPE_POLY_SET()
            single.AddOutline(fp.Outline(i))
            for h in range(fp.HoleCount(i)):
                single.AddHole(fp.Hole(i, h))
            other = pcbnew.B_Cu if lyr == pcbnew.F_Cu else pcbnew.F_Cu
            hit = [k for k, pos, ls in pts if lyr in ls and single.Contains(pos) and (not k.startswith('via') or in_fill(other, pos))]
            if not hit:
                bb = fp.Outline(i).BBox()
                print('NO-GND island', b.GetLayerName(lyr), i, round(mm(bb.GetX()), 2), round(mm(bb.GetY()), 2),
                      round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2))
