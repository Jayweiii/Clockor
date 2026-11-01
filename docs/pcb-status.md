# PCB status (hybrid v0.3)

## Placement

`scripts/place_and_route.py` builds each `.kicad_pcb` from the KiCad sexpr netlist (`review/*.net`): footprints via pcbnew, pads net-assigned, Edge.Cuts, GND zones outlined. Minute bar is **center-hub / LEDs both sides**.

| Board | Footprints | Tracks | Notes |
|-------|------------|--------|-------|
| base-controller | 39 | 0 | 1× DRV8313 + ULN2003A |
| hand-minute | 63 | 0 | Hall, 470µF+TVS, balance pads |

## Routing

**Not routed.** Freerouting CLI still hangs/crashes in autoroute. Follow-up: JAR freerouting or manual route, then `run_drc: true` in `kibot.yml`.

## ERC (local `kicad-cli sch erc --severity-all`, America/Los_Angeles 2026-11-01)

| Board | Errors | Warnings |
|-------|--------|----------|
| base-controller | 0 | 203 |
| hand-minute | 0 | 406 |

Waivers: `docs/erc-waivers.md`.

## DRC (local after place, still unrouted; America/Los_Angeles 2026-11-01)

| Board | Errors (incl. unconnected) | Warnings | Dominant |
|-------|----------------------------|----------|----------|
| base-controller | 170 (122 unconnected) | 8 | unconnected_items |
| hand-minute | 444 (289 unconnected) | 113 | unconnected + clearance/silk |

CI KiBot runs **ERC only** (`run_drc: false`) until routes exist. Reports: `review/*_drc.rpt`.
