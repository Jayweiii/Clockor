# PCB status (hybrid v0.4)

## Placement

`scripts/place_and_route.py` builds each `.kicad_pcb` from the KiCad sexpr netlist (`review/*.net`): footprints via pcbnew, pads net-assigned, Edge.Cuts, GND zones outlined. Minute bar is **center-hub / LEDs both sides**. J7/J8 moved so 5-pin connectors stay inside the 120×90 mm outline.

| Board | Footprints | Tracks | Notes |
|-------|------------|--------|-------|
| base-controller | 39 | 0 | 1× DRV8313 + ULN2003A |
| hand-minute | 63 | 0 | Hall, 470µF+TVS, balance pads |

## Routing attempt (Round 2)

| Method | Result |
|--------|--------|
| Specctra **DSN export** | OK (pcbnew.ExportSpecctraDSN) |
| Freerouting CLI v2.5.0 (`CLOCKOR_FREEROUTE=1`) | **Crash**: GraalVM `SerializationConstructorAccessor` / `ComponentOutline`; also warned J8 pad outside outline (fixed in place). No `.ses` produced. |
| `scripts/simple_route.py` MST L-routes | Connected many nets; **DRC shorts/crossings hundreds** — copper **reverted**; script kept for iteration. |

**CI:** `run_drc: false` remains. Enable only after local DRC reports **0 errors**.

## ERC (local `kicad-cli sch erc --severity-all`)

| Board | Errors | Warnings |
|-------|--------|----------|
| base-controller | 0 | ~203 |
| hand-minute | 0 | ~406 |

Waivers: `docs/erc-waivers.md`.

## DRC (placed, unrouted)

| Board | Violations | Unconnected |
|-------|------------|-------------|
| base-controller | ~57 + 122 unconnected | dominant unconnected_items |
| hand-minute | ~268 + 289 unconnected | dominant unconnected_items |

Reports: `review/*_drc.rpt`.
