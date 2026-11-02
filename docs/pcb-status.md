# PCB status — Clockor (updated 2026-11-02, base board routing pass v0.5)

## Base board (`base-controller`) — PARTIAL, not yet 0 unconnected

Produced by `scripts/route_base.py` (grid router, rebuilt in this pass; re-runnable: it strips tracks/vias/zones and re-routes). Schematic, footprints, outline and the minute board are untouched.

| Metric (`kicad-cli pcb drc`, repo rules) | Before (main) | After |
|---|---|---|
| Clearance / short errors | 0 | **0** |
| Unconnected items | 68 | **5** |
| Warnings | 9 (`track_dangling`, `hole_to_hole`) | 5 (`track_dangling`, stub ends of the unfinished nets) |

**Still unconnected (the blocker):**
- `/M1_CPH` (U5.2 to C20.1), `/M1_OUTC` (U5.9 to J3.3), `/USB_D+` (J2.A6/B6 to U1.14): the router found no path out of the 0.65 mm-pitch DRV8313 pin comb and the 0.5 mm-pitch USB-C pads once neighbouring nets were placed. The router is greedy (no rip-up); each ordering change fixed some nets and boxed in others. Needs rip-up/reroute or a manual fan-out in pcbnew.
- One GND pour island on F.Cu is not tied to the rest (needs one more stitching via or a pour tweak).

**Rules applied:** `VIN_12V` and `BUCK_SW` trunks at 1.5 mm (0.5 mm necks at fine-pitch pins); `+3V3` and `HR_OUT*` 0.5 mm; signals 0.25 mm (0.2 mm necks at fine pitch); GND pours on F.Cu and B.Cu with about 5 mm stitching vias; I2C kept clear of the motor phases (5 mm keep-out in the router).

**Tradeoffs / deviations:**
- **`+5V` (XL4015 output) is only 0.25-0.3 mm, not >=1.5 mm.** In this particular router ordering the wide attempt failed and fell back to the narrowest width that completed. Other orderings tried in this pass did route `+5V` at 1.5 mm but then left other nets unconnected. The approved rule is not met for this net.
- Motor phases `M1_OUTA/B/C` are **0.25-0.3 mm, not 1.5-2 mm**. The 0.65 mm pin pitch at U5 leaves no room for wide copper and the router uses one width per net. This does not meet the approved 2 A rule and must be widened by hand (or with a polygon) before the board is built.
- `M1_V3P3` is 0.25-0.3 mm (requested 0.5 mm).
- Fine-pitch pins use short exact-geometry escape stubs; `M1_EN1` pins on U5 use stub vias and join on B.Cu.
- The U1 antenna keep-out is honoured (no copper or pour under it).

**CI:** `kibot.base.yml` (strict, `ignore_unconnected: false`) is added and picked up for base-controller by the workflow. It stays **red** until the unconnected items above are closed. `hand-minute` is unchanged on `kibot.yml`.

Renders: `renders/base-controller_{front,back,3d}.{png,jpg}` and `_F_Cu.svg` / `_B_Cu.svg` are regenerated; previous versions are in `renders/before/`. The F_Cu/B_Cu PNG/JPG were removed rather than left stale (no SVG rasteriser was permitted in the job).

---

## Previous status (2026-11-01)

## Goal
Finish routing both boards without shorts, clear silk/courtyard/hole/dangling-via **errors**, target **0 non-unconnected DRC errors**, then enable DRC in KiBot CI (`ignore_unconnected: true` until UC=0).

## Result (honest)

| Board | ERC errors | ERC warnings | DRC shorts | Non-UC DRC **errors** | Unconnected | DRC warnings |
|-------|------------|--------------|------------|------------------------|-------------|--------------|
| `base-controller` | **0** | ~217 (`lib_symbol_issues`, `endpoint_off_grid`, …) | **0** | **0** | **68** | ~9 (`hole_to_hole`, `via_dangling`) |
| `hand-minute` | **0** | ~406 (same classes) | **0** | **0** | **74** | ~2 (`hole_to_hole`, `via_dangling`) |

**Shorts: 0.** **Non-unconnected DRC errors: 0** on both boards (clearance / hole_clearance / copper_edge / copper_sliver / track_dangling cleaned).

**Full 0-unconnected not reached** with the pattern/MST/via router on these dense hub layouts. Remaining UC nets need manual pcbnew work or a better autorouter. **CI `run_drc: true`** with `ignore_unconnected: true` (and existing `unconnected_items` filter) so the pipeline enforces zero real DRC errors without failing on unfinished nets.

Local reports: `review/*_drc.rpt`, `review/*_erc.rpt`.  
Review renders: `renders/*_{F_Cu,B_Cu,front,back,3d}.{png,jpg}` plus `.step` / `.glb`.

## How routed / cleaned
- `scripts/place_and_route.py` — placements + rules; GND pour **B.Cu only**.
- `scripts/finish_route.py` — pad/keepout obstacles, LED spines, MST, via patterns; short-clean.
- `scripts/second_pass.py` — DRC-pair reconnect (diminishing returns ~65–74 UC).
- Hygiene: strip F/B.CrtYd + dense silk; NPTH copper purge (J2 barrel); dangling track/via delete; hole_clearance 0; copper_edge 0.05 mm.

## Schematic Round 3 (base) — unchanged
- U6 `AH1806-W-7` hour-home hall + R22 10k + J9 → `/HR_HOME` (GPIO19).
- Hour drive **1:1** front-of-sweep stub axle (no hollow tube).

## Remaining PCB work
1. Manually finish ~68 / ~74 unconnected nets (or upgrade router).
2. Clear remaining `hole_to_hole` / `via_dangling` **warnings**.
3. Flip `ignore_unconnected` to false only when UC = 0.
