# PCB status — Clockor Round 3 (2026-11-01)

## Goal
Hand-route both boards (KiCad `pcbnew` Python) toward **0 DRC**, enable DRC in CI only if clean. If not reachable, get as close as possible **without shorts** and report honestly.

## Result (honest)

| Board | ERC errors | ERC warnings | DRC `shorting_items` | Other DRC | Unconnected |
|-------|------------|--------------|----------------------|-----------|-------------|
| `base-controller` | **0** | ~217 (mostly `endpoint_off_grid`, `lib_symbol_issues`) | **0** | ~108 (courtyard, silk, hole clearance, dangling vias, …) | ~94 |
| `hand-minute` | **0** | ~406 (same classes) | **0** | ~49 (silk/text/courtyard) | ~229 |

**Shorts cleared.** Both boards reach **0 `shorting_items`** after pad-aware careful routing + placement fixes (bypass caps / headers clear of MCU pads; hand slip header clear of ESP32-C3).

**0 full DRC is not reachable** with the current auto-MST / LED-spine router and dense hub placement: many nets remain unconnected, plus silk/courtyard/hole hygiene. **CI `run_drc` stays `false`** in `kibot.yml` — enabling it would fail the pipeline. Local reports live in `review/*_drc.rpt` / `review/*_erc.rpt`.

## How routed
- `scripts/place_and_route.py` — placements + design rules (min drill 0.2 mm, clearance 0.15 mm); GND pour on **B.Cu only** (no +5V/+3V3 pours that short LED pads).
- `scripts/careful_route.py` — pad-obstacle L-routes, LED daisy/spines, MST for other signals, iterative short-clean.
- Freerouting CLI skipped (GraalVM crash historically).

## Schematic Round 3 additions (base)
- U6 `AH1806-W-7` hour-home hall + R22 10k + J9 `Conn_01x03` → `/HR_HOME` on ESP GPIO19.
- Hour drive documented **1:1** (no gear ratio in firmware).

## Next PCB work (not blocking schematic/mech sign-off)
1. Manual finish of remaining unconnected nets in pcbnew (or improve router connectivity).
2. Courtyard / silk / hole-clearance cleanup.
3. Only then flip `kibot.yml` `run_drc: true`.
