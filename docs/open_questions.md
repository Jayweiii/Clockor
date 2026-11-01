# Open questions (hybrid v0.4)

## Closed in Round 2
- BLDC P/N → **Furitek KOMODO 2204 1400KV 12S14P** (alt T-Motor MN2204-1400).
- Slip ring → **Mercotac 205** (4 A, **2000 RPM** datasheet); Moflon MR204 alt.
- Hour mount → off-axis stepper + gear/belt → hollow hour shaft; only hand in front of clear dial.
- AS5600 magnet → shaft **rear**; Mercotac on **front** end.
- Firmware interlocks + hour half-step / coil de-energize → documented in `docs/firmware-interlocks.md`.
- Axial gap → **≥5 mm** bar tip to dial incl. runout (`docs/stack-up.md`).

## Still open
1. **Hour gear/belt ratio** — tooth counts so 28BYJ-48 half-steps map cleanly to 12 h; belt vs spur preference.
2. **Mercotac orientation** — shaft is roughly horizontal in desk clock; Mercotac prefers UP/vertical — validate life at our attitude or use a short vertical stub / 205-SS.
3. **Measured hub runout** — confirm ≥5 mm gap still holds after balance.
4. **DRV8313 margin** — if 2204 stall/spin current exceeds comfort, DRV8316 + current sense.
5. **TPS54560** — only if XL4015 thermals fail at full LED + spin load.
6. **Guard / hub CAD detail** — clamp hub STEP and polycarbonate guard before first spin test.
7. **PCB routing** — still unrouted or partial; enable `run_drc: true` in CI only after 0 DRC errors.
8. **Firmware implementation** — interlocks specified; code not yet written against ESP-IDF/Arduino target.
