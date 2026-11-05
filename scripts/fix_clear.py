"""Shrink tracks of the given nets that take part in clearance violations.
Usage: fix_clear.py board.kicad_pcb "+5V,..."   (rewrites board in place)"""
import json, subprocess, sys, pcbnew
path, nets = sys.argv[1], set(sys.argv[2].split(','))
nm, mm = pcbnew.FromMM, pcbnew.ToMM
for it in range(8):
    subprocess.run(['kicad-cli', 'pcb', 'drc', '--severity-all', '--all-track-errors', '--format', 'json',
                    '-o', '/tmp/fc.json', path], capture_output=True)
    v = [x for x in json.load(open('/tmp/fc.json'))['violations'] if x['type'] == 'clearance']
    b = pcbnew.LoadBoard(path)
    n = 0
    for x in v:
        for i in x['items']:
            t = b.GetItem(pcbnew.KIID(i['uuid']))
            t = pcbnew.Cast_to_PCB_TRACK(t) if t is not None and t.GetClass() == 'PCB_TRACK' else None
            if t and t.GetNetname() in nets and t.GetWidth() > nm(0.25):
                t.SetWidth(max(nm(0.25), t.GetWidth() - nm(0.2)))
                n += 1
    print('pass', it, 'violations', len(v), 'shrunk', n)
    if not v or not n:
        break
    pcbnew.SaveBoard(path, b)
