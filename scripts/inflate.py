"""Greedy in-place widening: set target nets' tracks to their wanted width, run DRC,
shrink only the offending tracks one step, repeat until clean.
Usage: inflate.py in.kicad_pcb out.kicad_pcb  (works on a copy; nothing else is touched)"""
import pcbnew, sys, json, subprocess, os, tempfile, shutil

SRC, DST = sys.argv[1], sys.argv[2]
WANT = {'+5V': 1.5, '/M1_OUTA': 1.5, '/M1_OUTB': 1.5, '/M1_OUTC': 1.5, '/VIN_12V': 1.5, 'GND': 1.0}
STEPS = [1.5, 1.2, 1.0, 0.8, 0.6, 0.5, 0.4, 0.3, 0.25]
mm = pcbnew.FromMM
b = pcbnew.LoadBoard(SRC)
cur = {}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_TRACK' and t.GetNetname() in WANT:
        cur[t.m_Uuid.AsString()] = (t, min(WANT[t.GetNetname()], 99), t.GetWidth() / 1e6)
orig = {u: v[2] for u, v in cur.items()}
level = {u: STEPS.index(min(STEPS, key=lambda s: abs(s - WANT[v[0].GetNetname()]))) for u, v in cur.items()}
# never widen beyond want, never narrow below original
for u, (t, _, w0) in cur.items():
    t.SetWidth(mm(max(STEPS[level[u]], w0)))
d = os.path.dirname(os.path.abspath(SRC))
work = os.path.join(d, '_inflate_tmp.kicad_pcb')
shutil.copy(SRC.replace('.kicad_pcb', '.kicad_pro'), work.replace('.kicad_pcb', '.kicad_pro'))
for it in range(40):
    b.Save(work)
    out = work + '.json'
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--severity-all', '--all-track-errors', '--format', 'json',
                    '-o', out, work], check=False, capture_output=True)
    rep = json.load(open(out))
    bad = set()
    for v in rep.get('violations', []):
        if v['type'] in ('clearance', 'shorting_items', 'hole_clearance', 'copper_edge_clearance', 'track_width'):
            for i in v['items']:
                if i['uuid'] in cur:
                    bad.add(i['uuid'])
    print('iter', it, 'violations', len(rep.get('violations', [])), 'offending', len(bad), flush=True)
    if not bad:
        break
    for u in bad:
        t, _, w0 = cur[u]
        if t.GetWidth() / 1e6 <= w0 + 1e-6:
            continue
        level[u] += 1
        t.SetWidth(mm(max(STEPS[min(level[u], len(STEPS) - 1)], w0)))
b.Save(DST)
for f in (work, work.replace('.kicad_pcb', '.kicad_pro'), work + '.json'):
    os.path.exists(f) and os.remove(f)
