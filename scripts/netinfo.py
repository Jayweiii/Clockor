#!/usr/bin/env python3
"""Print pads and copper of one net: python3 -I scripts/netinfo.py NET [pcb]"""
import sys
import pcbnew

net = sys.argv[1]
pcb = sys.argv[2] if len(sys.argv) > 2 else 'hardware/base-controller/base-controller.kicad_pcb'
b = pcbnew.LoadBoard(pcb)
mm = pcbnew.ToMM
for fp in b.GetFootprints():
    for p in fp.Pads():
        if p.GetNetname() == net:
            print('PAD', fp.GetReference(), p.GetNumber(), round(mm(p.GetPosition().x), 3), round(mm(p.GetPosition().y), 3),
                  [b.GetLayerName(l) for l in p.GetLayerSet().Seq()])
for t in b.GetTracks():
    if t.GetNetname() == net:
        print(t.GetClass(), b.GetLayerName(t.GetLayer()), round(mm(t.GetStart().x), 3), round(mm(t.GetStart().y), 3),
              round(mm(t.GetEnd().x), 3), round(mm(t.GetEnd().y), 3))
ds = b.GetDesignSettings()
print('min clearance', mm(ds.m_MinClearance), 'min track', mm(ds.m_TrackMinWidth), 'min via', mm(ds.m_ViasMinSize))
