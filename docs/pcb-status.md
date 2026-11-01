# PCB status — v0.6 (2026-11-01)

## Summary

The **v0.6 schematics** are regenerated and pass `scripts/sch_netcheck.py --check` (0 problems on both boards).
The **PCB files are still the v0.5 layouts** and **do not match** the v0.6 netlists. Do not fabricate them.

KiBot CI: ERC + schematic PDF + BOM run; DRC, Gerbers, drill and PCB PDF are off (`run_by_default: false`) until re-layout.

## Why the v0.5 copper is not reusable as-is

| Item | v0.5 layout |
|---|---|
| USB-C VBUS pads | Routed to **GND** (schematic bug); copper shorts host VBUS |
| Rotor TVS D40 | Reversed vs. `D_SMA` pad 1 = cathode → shorts +5 V |
| Unrouted nets | ~68 (base) / ~74 (rotor) |
| Silkscreen | **Deleted** by `finish_route.py` (no polarity / pin-1 marks) |
| Courtyards | **Deleted** on U1 and crowded parts to pass DRC |
| Rules | Hole clearance 0, copper-to-edge 0.05 mm — below fab capability |
| Hole-to-hole | Stacked GND vias 0.2 mm apart (overlapping drills) |

## v0.6 layout procedure

1. `KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols python3 scripts/rebuild_boards.py --sch-only` (schematics only; keeps the `.kicad_pro` rules and the existing `.kicad_pcb`).
2. In pcbnew: **Tools → Update PCB from Schematic** (F8). New parts: base U7, D3, R23–R26, C23–C27, J10 (U6 removed); rotor J2, TP5/TP6, R3/R4, C6/C7 (C5 changes to a 7343 footprint, U4 changes to SOT-23).
3. **Delete all v0.5 tracks and vias** and route by hand. Priorities:
   - Base: DRV8313 VM caps C23/C24 at pins 4/11; the exposed pad needs a thermal via array to the B.Cu GND pour; XL4015 hot loop (C1–U2–D1) tight; USB D± as a 90 Ω pair through U7.
   - Rotor: symmetric copper mass about the hub; C5/C7 and U1 at the hub (lowest g); LED chain on one layer; DRV5023 at the radius the fixed magnet passes.
4. Restore silkscreen (`scripts/finish_route.py::hide_silk` now hides only Value text).
5. Board rules (now in the `.kicad_pro`): clearance 0.15, hole clearance 0.25, hole-to-hole 0.25, copper-to-edge 0.3 mm.
6. DRC must be **clean including unconnected items**. Then set `run_drc: true`, remove `ignore_unconnected`, and drop `run_by_default: false` from the fab outputs in `kibot.yml`.

The experimental routers (`simple_route.py`, `careful_route.py`, `finish_route.py`, `second_pass.py`) are kept for reference. Their output plateaued at ~70 unconnected nets per board; hand routing is the expected path.
