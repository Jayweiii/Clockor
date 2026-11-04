#!/usr/bin/env python3
"""For each candidate signal net: remove its copper, refill, report GND cluster count.
python3 -I scripts/gnd_probe.py [pcb]"""
import sys
import pcbnew

PCB = sys.argv[1] if len(sys.argv) > 1 else 'hardware/base-controller/base-controller.kicad_pcb'


def fill(b):
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())


def clusters(b):
    gnd = b.FindNet('GND').GetNetCode()
    isl = []
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

    def at(l, p):
        return [k for k, (ll, s, bb) in enumerate(isl) if ll == l and bb.Contains(p) and s.Contains(p)]

    def un(ids):
        for a in ids[1:]:
            par[find(a)] = find(ids[0])
    for t in b.GetTracks():
        if t.GetNetCode() != gnd:
            continue
        if t.GetClass() == 'PCB_VIA':
            un(at(pcbnew.F_Cu, t.GetPosition()) + at(pcbnew.B_Cu, t.GetPosition()))
        else:
            un(at(t.GetLayer(), t.GetStart()) + at(t.GetLayer(), t.GetEnd()))
    for fp in b.GetFootprints():
        for p in fp.Pads():
            if p.GetNetCode() == gnd:
                ids = []
                for l in (pcbnew.F_Cu, pcbnew.B_Cu):
                    if p.IsOnLayer(l):
                        ids += at(l, p.GetPosition())
                un(ids)
    return len({find(k) for k in range(len(isl))})


if __name__ == '__main__':
    b = pcbnew.LoadBoard(PCB)
    fill(b)
    print('base', clusters(b))
    cand = ['/M1_IN1', '/M1_IN3', '/M1_CPL', '/M1_OUTB', '/M1_OUTA', '/M1_OUTC', '/M1_VCP', '/M1_CPH',
            '/VIN_12V', '/M1_IN2', '/M1_nFAULT', '/M1_V3P3', '/M1_EN1']
    for n in cand:
        b = pcbnew.LoadBoard(PCB)
        for t in list(b.GetTracks()):
            if t.GetNetname() == n:
                b.RemoveNative(t)
        fill(b)
        print(n, clusters(b), flush=True)
