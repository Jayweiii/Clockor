# Open questions (hybrid v0.5)

## Closed in Round 2 / Round 3
- BLDC P/N → **Furitek KOMODO 2204 1400KV 12S14P**.
- Slip ring → **SenRing G012 brush PRIMARY** (≥5000 RPM, 5 A, linked PDF); **Mercotac 205 ALT** with orientation + Hg disposal notes.
- Hour mount → **stub axle** at dial-center bearing, **1:1** off-axis drive, entirely in front of bar sweep (no hollow tube).
- Hour home → **AH1806** on base schematic (U6 / J9).
- AS5600 magnet → shaft **rear**; slip on **front**.
- Firmware interlocks + hour half-step / coil de-energize documented.
- Axial gap → **≥5 mm** bar tip to dial incl. runout.

## Still open
1. **Exact stub bearing / pulley P/Ns** — flange bearing + GT2 1:1 pulley tooth count for dial thickness.
2. **SenRing shaft adapter** — collar for Ø5 shaft into 12.7 mm bore (or custom stub).
3. **Measured hub runout** — confirm ≥5 mm gap after balance.
4. **DRV8313 margin** — DRV8316 + sense only if torque short.
5. **TPS54560** — only if XL4015 thermals fail.
6. **Guard / hub CAD detail** — clamp hub STEP + polycarbonate guard before first spin test.
7. **PCB DRC** — see `docs/pcb-status.md`; enable CI `run_drc` only at 0 errors (or report honest near-miss).
8. **Firmware implementation** — interlocks specified; code not yet written.
