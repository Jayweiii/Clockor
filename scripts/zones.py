#!/usr/bin/env python3
"""List filled GND zone islands (bounding boxes) per layer: python3 scripts/zones.py pcb"""
import sys
import pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
for z in b.Zones():
    for lyr in z.GetLayerSet().Seq():
        fp = z.GetFilledPolysList(lyr)
        for i in range(fp.OutlineCount()):
            bb = fp.Outline(i).BBox()
            print(b.GetLayerName(lyr), i, 'pts', fp.Outline(i).PointCount(),
                  round(mm(bb.GetX()), 2), round(mm(bb.GetY()), 2),
                  round(mm(bb.GetWidth()), 2), round(mm(bb.GetHeight()), 2))
