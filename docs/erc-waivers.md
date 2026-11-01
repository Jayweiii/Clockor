# ERC (v0.6)

## Connectivity check without KiCad: `scripts/sch_netcheck.py`

`rebuild_boards.py` ends every run with `sch_netcheck.check()` and fails on:

- **SHORT**: one net carrying two different label names (except the intentional aliases `SLIP_5V=+5V`, `SLIP_GND=GND`, `M1_EN_ALL=EN1..3`, `M1_nSLEEP=nRESET`).
- **COLLISION**: a pin flagged no-connect that touches another net. This is how v0.5's USB-C CC1 ended up on +5V.
- **FLOATING**: a pin with no connection and no no-connect flag.
- **OVERLAP**: a pin or wire end lying on another wire's interior. KiCad doesn't join these, but they become shorts with one stray junction.
- **UNDRIVEN**: power-input pins with no power output or PWR_FLAG on the net.

The netlister was validated against KiCad 9.0.7 `kicad-cli sch export netlist` on the v0.5 sheets: both boards matched exactly, group for group (`--compare review/<board>.net`).

| Sheet | v0.5 | v0.6 |
|---|---|---|
| base-controller | 4 (CC1 collision, 6-way enable/sleep/reset tie, 2 button-pin overlaps) | **0** |
| hand-minute | 120 (LED-grid stub overlaps) | **0** |

## KiCad ERC

The v0.5 `kicad-cli sch erc` reports in `review/*_erc.rpt` (0 errors) are kept for history. **The v0.6 sheets have not been through kicad-cli ERC yet** (KiCad wasn't available where they were generated); KiBot CI runs it on push. Expected warning classes, unchanged from v0.5:

1. **endpoint_off_grid**: generated stubs / library pin tips not on the 1.27 mm grid.
2. **lib_symbol_issues**: headless ERC without a global sym-lib-table; symbols are embedded in each `.kicad_sch`.
3. **multiple_net_names**: the intentional aliases above.
4. **footprint_link_issues**: footprint filter warnings; footprints resolve in the PCB.

Do **not** waive `pin_to_pin`, `pin_not_connected`, `label_dangling`, or `power_pin_not_driven` at error severity.
