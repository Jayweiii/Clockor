# Open questions (hybrid v0.6)

## Closed in v0.6
- Hour drive: **coaxial Ø3 hour shaft** inside a hollow minute tube, 28BYJ-48 at the rear, direct 1:1 coupler. Replaces the v0.5 front stub + belt, which covered the POV image.
- Minute motor: **hollow-shaft gimbal BLDC ~100 KV on 24 V** (replaces the Furitek 2204 1400 KV).
- Minute encoder: **MA730 side-shaft** on SPI (`J10`); AS5600 kept as a bench fallback on `J5`.
- Rotor index: **DRV5023** (always-on), replacing AH1806 (duty-cycled).
- Programming: rotor `J2` UART header + USB pogo pads; base USB-C fixed.
- All v0.5 schematic defects in `docs/design-review-v0.6.md` §2 are fixed in the generator.

## Still open
1. **Gimbal motor bore**: confirm the purchased motor's hollow shaft passes a Ø3 shaft (or a Ø6 tube). If not, use a 4108-class hollow motor.
2. **MA730 side-shaft accuracy** with a 12/6 ring magnet; ±1° is plenty for parking a minute hand.
3. **XL4015 VC pin**: v0.6 follows the typical-application circuit (1 µF VC→VIN). Confirm against the XLSEMI datasheet before layout.
4. **SenRing shaft collar**: 12.7 mm bore → Ø6 tube collar design.
5. **Measured hub runout**: confirm the ≥ 5 mm gap after balancing.
6. **Guard / hub CAD**: clamp hub STEP + polycarbonate guard before the first spin test.
7. **PCB re-layout**: both boards need "Update PCB from Schematic" + hand routing (`docs/pcb-status.md`).
8. **Firmware**: interlocks specified (`docs/firmware-interlocks.md`), code not written.
9. **LCSC ids** for the new parts (DRV5023, USBLC6, SS34, polymer caps, MA730).
10. **VIN monitor**: an ADC divider on VIN_24V would let firmware refuse spin-up on a low supply (not in v0.6).
