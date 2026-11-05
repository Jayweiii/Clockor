"""Per-net min track width and length under 1.5 mm. Usage: widths.py board.kicad_pcb"""
import pcbnew, sys, collections
b = pcbnew.LoadBoard(sys.argv[1])
mm = pcbnew.ToMM
d = collections.defaultdict(lambda: [9, 0, 0])
for t in b.GetTracks():
    if t.GetClass() != 'PCB_TRACK':
        continue
    n = t.GetNetname(); w = mm(t.GetWidth()); L = mm(t.GetLength())
    r = d[n]; r[0] = min(r[0], w); r[2] += L
    if w < 1.5:
        r[1] += L
for n, (w, s, L) in sorted(d.items(), key=lambda x: -x[1][1]):
    if s > 0 or w < 1.5:
        print(f"{n:16} min {w:.2f}  <1.5mm {s:6.1f}  total {L:6.1f}")
