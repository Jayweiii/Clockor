#!/usr/bin/env python3
"""Regenerate bom/*.csv straight from the schematics (no KiCad needed).

v0.5's CSVs were hand-maintained and drifted (base BOM was missing U6/R22/J9,
master BOM still listed the Mercotac). This reads every in-BOM symbol from the
.kicad_sch files so the BOM can't disagree with the schematic.

LCSC numbers: only parts whose LCSC id was already recorded in the repo are
filled in; everything else is left blank on purpose — confirm at order time.
"""
from __future__ import annotations

import csv
import re
import sys
from collections import OrderedDict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from sch_netcheck import child, children, parse_sexpr, prop  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BOARDS = {"base-controller": "base_controller_bom.csv", "hand-minute": "hand_minute_bom.csv"}

# LCSC ids carried over from docs/lcsc_sources.md (v0.5). Verify stock before ordering.
LCSC = {
    "ESP32-S3-WROOM-1-N16R8": "C2913202",
    "ESP32-C3-MINI-1-N4": "C2934560",
    "DRV8313PWPR": "C92482",
    "ULN2003ADR": "C7512",
    "XL4015E1": "C51661",
    "AMS1117-3.3": "C6186",
    "ME6211C33M5G-N": "C235316",
    "SN74AHCT125PWR": "C5947",
    "APA102-2020": "C22439302",
    "SMAJ5.0A": "C83329",
    "SS54": "C8678",
}

# Off-board mechanical / satellite parts (v0.6 coaxial architecture). ESTIMATE = confirm at order.
MECH = [
    ("Hollow-shaft gimbal BLDC, 2804 class, ~100 KV, 7 pole pairs (e.g. iPower GM2804H-100T)", "Minute drive, hour shaft passes through bore", 1, "mech", "ESTIMATE: confirm bore ≥ 3.5 mm"),
    ("SenRing G012 through-bore brush slip ring (2 circuits used)", "5 V + GND to rotor, ≥5000 RPM / 5 A", 1, "mech", "https://www.senring.com/high-speed-slip-ring/g012-12.html"),
    ("28BYJ-48 5 V geared stepper", "Hour drive, coaxial at rear, direct coupler", 1, "mech", "common"),
    ("Ø3 mm ground steel hour shaft + 2× MR63ZZ (3×6×2.5) bearings inside minute tube", "Inner hour shaft", 1, "mech", "ESTIMATE"),
    ("Hollow minute tube Ø6/Ø4 mm (or motor's hollow shaft + extension)", "Minute shaft", 1, "mech", "ESTIMATE"),
    ("MagAlpha MA730 on satellite PCB + diametric ring magnet on minute tube (side-shaft)", "Minute absolute angle (SPI, J10)", 1, "mech", "verify side-shaft accuracy per MPS app note"),
    ("AH1806 (or any hall switch) + Ø2×1 magnet on hour coupler", "Hour home via J9", 1, "mech", "slow index, micropower part OK"),
    ("Clear acrylic dial 2 mm, Ø5 mm centre hole", "Face; ≥5 mm above bar tip incl. runout", 1, "mech", "local laser cut"),
    ("24 V ≥2 A barrel PSU (5.5×2.1)", "System supply", 1, "mech", "common"),
]


def board_parts(sch: Path):
    root = parse_sexpr(sch.read_text())
    parts: "OrderedDict[str, tuple[str, str]]" = OrderedDict()
    for sym in children(root, "symbol"):
        ref = prop(sym, "Reference")
        in_bom = child(sym, "in_bom")
        if ref.startswith("#") or (in_bom and in_bom[1] == "no"):
            continue
        parts.setdefault(ref, (prop(sym, "Value"), prop(sym, "Footprint")))

    def nat(r):
        m = re.match(r"([A-Za-z]+)(\d+)", r)
        return (m.group(1), int(m.group(2))) if m else (r, 0)

    return sorted(parts.items(), key=lambda kv: nat(kv[0]))


def main():
    agg: "OrderedDict[tuple[str, str], list[str]]" = OrderedDict()
    for board, out in BOARDS.items():
        rows = board_parts(ROOT / "hardware" / board / f"{board}.kicad_sch")
        with open(ROOT / "bom" / out, "w", newline="") as f:
            w = csv.writer(f, lineterminator="\n")
            w.writerow(["Ref", "Value", "Footprint", "LCSC", "Board"])
            for ref, (val, fp) in rows:
                w.writerow([ref, val, fp, LCSC.get(val, ""), board])
                agg.setdefault((val, fp), []).append(f"{board}:{ref}")
        print(f"{out}: {len(rows)} parts")
    with open(ROOT / "bom" / "master_bom_aggregated.csv", "w", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["Value", "Footprint", "LCSC", "Qty", "Refs"])
        for (val, fp), refs in sorted(agg.items()):
            w.writerow([val, fp, LCSC.get(val, ""), len(refs), ";".join(refs)])
        for row in MECH:
            w.writerow(row)
    print("master_bom_aggregated.csv written")


if __name__ == "__main__":
    main()
