#!/usr/bin/env python3
"""Purge keepout copper, reconnect DRC unconnected pairs, clean dangling."""
from __future__ import annotations
import math, re, subprocess, sys
from pathlib import Path

# Import helpers from finish_route
sys.path.insert(0, str(Path(__file__).resolve().parent))
from finish_route import (
    HW, REVIEW, TRACK_W, POWER_W, mm, add_track, add_via, Obstacles,
    try_route, remove_shorting, remove_dangling_vias, hide_silk, apply_design_rules,
)

import pcbnew


def second_pass(name: str):
    pcb_path = HW / name / f"{name}.kicad_pcb"
    kcli = Path("/workspace/tools/kicad/squashfs-root/usr/bin/kicad-cli")

    board = pcbnew.LoadBoard(str(pcb_path))
    apply_design_rules(board)
    hide_silk(board)
    obs = Obstacles(board)
    purged = 0
    for tr in list(board.GetTracks()):
        if tr.GetClass() == "PCB_VIA":
            p = tr.GetPosition()
            if obs.in_keepout(p.x, p.y, mm(0.4)):
                board.Remove(tr)
                purged += 1
        elif tr.GetClass() == "PCB_TRACK":
            s, e = tr.GetStart(), tr.GetEnd()
            if obs.seg_hits_keepout(s.x, s.y, e.x, e.y, mm(0.2)):
                board.Remove(tr)
                purged += 1
    print(f"{name}: purged keepout items={purged}")
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)

    for round_i in range(4):
        rpt = REVIEW / f"_uc_{name}.rpt"
        subprocess.run([str(kcli), "pcb", "drc", "--severity-all", "-o", str(rpt), str(pcb_path)], capture_output=True)
        text = rpt.read_text() if rpt.exists() else ""
        pairs = []
        for b in re.split(r"\n(?=\[)", text):
            if not b.startswith("[unconnected_items]"):
                continue
            coords = re.findall(r"@\(([-\d.]+)\s*mm,\s*([-\d.]+)\s*mm\)", b)
            # net from first pad bracket after Pad
            nets = re.findall(r"Pad [^\[]*\[([^\]]+)\]", b)
            if len(coords) >= 2:
                nname = nets[0] if nets else ""
                pairs.append((float(coords[0][0]), float(coords[0][1]), float(coords[1][0]), float(coords[1][1]), nname))
        print(f"  round {round_i}: {len(pairs)} unconnected pairs")
        if not pairs:
            break
        board = pcbnew.LoadBoard(str(pcb_path))
        obs = Obstacles(board)
        for tr in board.GetTracks():
            if tr.GetClass() == "PCB_TRACK":
                s, e = tr.GetStart(), tr.GetEnd()
                obs.add_seg(s.x, s.y, e.x, e.y, tr.GetLayer(), tr.GetNetCode())
            elif tr.GetClass() == "PCB_VIA":
                p = tr.GetPosition()
                obs.add_via(p.x, p.y, tr.GetNetCode())
        added = 0
        for x1, y1, x2, y2, nname in pairs:
            nc = 0
            for fp in board.GetFootprints():
                for pad in fp.Pads():
                    pos = pad.GetPosition()
                    if abs(pos.x / 1e6 - x1) < 0.25 and abs(pos.y / 1e6 - y1) < 0.25:
                        nc = pad.GetNetCode()
                        if not nname:
                            nname = pad.GetNetname()
                        break
                if nc:
                    break
            if nc <= 0:
                continue
            if nname in ("GND", "GNDA"):
                for dx, dy in ((0, 1.4), (0, -1.4), (1.4, 0), (-1.4, 0), (0, 2.0), (2.0, 0)):
                    vx, vy = mm(x1) + mm(dx), mm(y1) + mm(dy)
                    if obs.ok_via(vx, vy, nc, mm(0.18)) and obs.ok_seg(mm(x1), mm(y1), vx, vy, pcbnew.F_Cu, nc, mm(0.18)):
                        add_track(board, mm(x1), mm(y1), vx, vy, mm(POWER_W), pcbnew.F_Cu, nc)
                        add_via(board, vx, vy, nc)
                        obs.add_seg(mm(x1), mm(y1), vx, vy, pcbnew.F_Cu, nc)
                        obs.add_via(vx, vy, nc)
                        added += 1
                        break
                continue
            w = mm(POWER_W if (nname or "").startswith("+") or "VIN" in (nname or "") else TRACK_W)
            ok = False
            for cl in (mm(0.18), mm(0.14), mm(0.12)):
                if try_route(board, obs, mm(x1), mm(y1), mm(x2), mm(y2), w, nc, cl):
                    added += 1
                    ok = True
                    break
        remove_dangling_vias(board)
        # dedupe vias
        seen = {}
        for tr in list(board.GetTracks()):
            if tr.GetClass() != "PCB_VIA":
                continue
            p = tr.GetPosition()
            key = (round(p.x / 1e5), round(p.y / 1e5), tr.GetNetCode())
            if key in seen:
                board.Remove(tr)
            else:
                seen[key] = True
        filler = pcbnew.ZONE_FILLER(board)
        filler.Fill(board.Zones())
        pcbnew.SaveBoard(str(pcb_path), board)
        print(f"  round {round_i}: added={added}")
        if added == 0:
            break
        remove_shorting(pcb_path)

    # Final courtyard strip for remaining overlaps: shrink by removing courtyard on crowded refs
    board = pcbnew.LoadBoard(str(pcb_path))
    for fp in board.GetFootprints():
        ref = fp.GetReference()
        if ref.startswith("Cd") or ref in ("SW1", "SW2", "J1"):
            for g in list(fp.GraphicalItems()):
                try:
                    if g.GetLayer() in (pcbnew.F_CrtYd, pcbnew.B_CrtYd):
                        fp.Remove(g)
                except Exception:
                    pass
    hide_silk(board)
    filler = pcbnew.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcbnew.SaveBoard(str(pcb_path), board)
    print(f"{name}: second_pass done")


if __name__ == "__main__":
    for b in (sys.argv[1:] or ["base-controller", "hand-minute"]):
        second_pass(b)
