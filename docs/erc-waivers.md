# ERC waivers (errors = 0 on all boards)

Measured 2026-11-01 (America/Los_Angeles) with KiCad 9.0.7 `kicad-cli sch erc --severity-all`.

| Board | Errors | Warnings |
|-------|--------|----------|
| base-controller | 0 | 237 |
| hand-minute | 0 | 380 |
| hand-hour | 0 | 332 |

## Waived warning classes

1. **endpoint_off_grid** (majority) — Generated wire stubs / pin tips land on 0.01 mm geometry from library pins that are not on the 1.27 mm schematic grid. Connectivity is correct; grid snap would move pins off the symbol. Accept for generated sheets; clean in interactive edit if desired.

2. **lib_symbol_issues** — Headless ERC without a full global sym-lib-table reports “library not included” for stock `power` / `Device` / Espressif while symbols are **embedded** in each `.kicad_sch`. Not a missing-symbol failure at ERC time (errors = 0). KiBot/CI uses project `sym-lib-table` + embedded libs.

3. **multiple_net_names** (base only, 4) — Intentional aliases (e.g. motor EN fan-out / slip-ring net ties) where two labels share copper. Netlist picks one name; electrically OK.

4. **footprint_link_issues** (base, 3) — Harmless footprint filter / link warnings on connectors; footprints resolve in PCB + netlist.

Do **not** waive `pin_to_pin`, `pin_not_connected`, `label_dangling`, or `power_pin_not_driven` at error severity — those were driven to zero before commit.
