import sys
import pcbnew
b = pcbnew.LoadBoard('hardware/base-controller/base-controller.kicad_pcb')
mm = pcbnew.ToMM
refs = sys.argv[1:]
for f in b.GetFootprints():
    if f.GetReference() not in refs:
        continue
    for p in f.Pads():
        bb = p.GetBoundingBox()
        print(f.GetReference(), p.GetNumber(), p.GetNetname(), 'thru' if p.GetAttribute() in (pcbnew.PAD_ATTRIB_PTH, pcbnew.PAD_ATTRIB_NPTH) else 'smd',
              p.GetShape(), 'x%.2f..%.2f y%.2f..%.2f' % (mm(bb.GetLeft()), mm(bb.GetRight()), mm(bb.GetTop()), mm(bb.GetBottom())),
              'drill', mm(p.GetDrillSizeX()))
