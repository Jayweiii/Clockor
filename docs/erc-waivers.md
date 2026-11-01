# ERC waivers (errors = 0 on both hybrid boards)

Measured 2026-11-01 (America/Los_Angeles) with KiCad 9.0.7 `kicad-cli sch erc --severity-all`.

| Board | Errors | Warnings |
|-------|--------|----------|
| base-controller | 0 | 203 |
| hand-minute | 0 | 406 |

## Waived warning classes

1. **endpoint_off_grid** (majority) — Generated wire stubs / library pin tips not on 1.27 mm grid. Connectivity OK.
2. **lib_symbol_issues** — Headless ERC without full global sym-lib-table; symbols are **embedded** in each `.kicad_sch`.
3. **multiple_net_names** — Intentional aliases / shared labels; netlist picks one name.
4. **footprint_link_issues** — Harmless connector footprint filter warnings; footprints resolve in PCB.

Do **not** waive `pin_to_pin`, `pin_not_connected`, `label_dangling`, or `power_pin_not_driven` at error severity.
