# PCB status

## Placement

`scripts/place_and_route.py` builds each `.kicad_pcb` from the KiCad sexpr netlist (`review/*.net`): all BOM footprints via pcbnew, pads net-assigned, Edge.Cuts rectangle, GND zones outlined (unfilled).

| Board | Footprints | Tracks | Vias |
|-------|------------|--------|------|
| base-controller | 43 | 0 | 0 |
| hand-minute | 55 | 0 | 0 |
| hand-hour | 49 | 0 | 0 |

## Routing

**Not routed.** Freerouting CLI v2.5.0 (native/GraalVM) exports DSN then crashes in autoroute (`UnsupportedFeatureError` / `ComponentOutline` serialization). No `.ses` produced.

## DRC (local `kicad-cli pcb drc --severity-all`, 2026-11-01)

| Board | Errors (incl. unconnected) | Warnings | Dominant |
|-------|----------------------------|----------|----------|
| base-controller | 185 (141 unconnected) | 12 | unconnected_items |
| hand-minute | 375 (286 unconnected) | 68 | unconnected + LED pitch clearance |
| hand-hour | 333 (250 unconnected) | 62 | same |

CI KiBot currently runs **ERC only** (`run_drc: false`) until routes exist. Reports: `review/*_drc.rpt`.
