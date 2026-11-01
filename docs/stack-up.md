# Mechanical stack-up (hybrid v0.6 — coaxial hour shaft)

All lengths in mm. **ESTIMATE** = pending measured parts. **LOCKED** = carried from earlier rounds.
Values below are the `cad/build_assembly.py` constants (`cad/STACK_UP_NOTES.txt` is regenerated on every CAD run).

## Axial order (rear → front, +Z toward dial)

| # | Z (mm) | Element | Notes |
|---|---|---|---|
| 1 | −60 … −41 | **28BYJ-48** (5 V) | Body Ø28×19; **output shaft on the clock axis** (body offset 8 mm) |
| 2 | −35 … −27 | **Coupler** 5 → 3 mm | Hour-home magnet Ø2×1 on its rim → hall on `J9` |
| 3 | −22 … −19 | **Ring magnet** on minute tube | Diametric, OD 12 / ID 6; **MA730** satellite beside it (side-shaft), `J10` |
| 4 | −14 … 0 | **Hollow-shaft gimbal BLDC** (2804 class) | Minute tube passes through the bore. ESTIMATE: confirm bore ≥ 6 mm or use motor hollow shaft + extension |
| 5 | 0 … 4 | Base plate | |
| 6 | 6 / 22 | Bearings on minute tube | OD 16, ID 6 ESTIMATE |
| 7 | 28 … 50 | **SenRing G012** through-bore brush slip ring | Bore 12.7 → collar on Ø6 tube; stator → `J7`, rotor → hub |
| 8 | 52 | Hub + `hand-minute` bar | 160 mm overall, balanced |
| 9 | 54.5 … 59.5 | **Air gap ≥ 5 LOCKED** | Bar tip / LED top → dial underside, incl. 1.0 runout budget |
| 10 | 59.5 … 61.5 | Clear acrylic dial | **Ø5 centre hole** (hour shaft clearance only) |
| 11 | 63 | **Hour hand** | 60 mm, on the Ø3 hour shaft — **the only part in front of the dial** |

Minute tube runs Z −23 … 55.1 (ends ≥ 4 mm behind the dial). Hour shaft runs Z −35 … 65.5.

## Hour drive (v0.6)

```
 hour hand ──┐                                    (front)
 dial ═══════╪══════  Ø5 hole
             │  ← Ø3 hour shaft (inside the tube on 2× MR63 3×6×2.5)
 bar ════════╪═══════ hub on Ø6/Ø4 minute tube
 slip ring  [│]
 BLDC      [[│]]      hollow-shaft gimbal motor
 ring mag   [│]  ▭ MA730
 coupler    [■]  ● hour-home magnet → hall (J9)
 28BYJ-48   [▓]                                   (rear)
```

**Rules:**
- The hour drive is **1:1** through a direct coupler. There is no belt or gear, so backlash is just the 28BYJ-48 gearbox's (~1–2°, fine for an hour hand).
- **Nothing but the hour hand** is in front of the dial or inside the bar's swept disk.
- The minute tube and hour shaft are independent: the MR63 bearings spin at bar speed relative to the hour shaft. Their drag is negligible against the 28BYJ-48 gearbox's friction (the coils are de-energized between moves).

## Why not the v0.5 front stub + belt?

v0.5 (Chief Round 3) mounted the 28BYJ-48 **on the dial face** at x = 48 mm with a 1:1 belt to a stub axle. The bar sweeps r ≤ 80 mm behind a **clear** dial, so the stepper body, both pulleys and the belt sat over the POV image. Moving them behind the dial would put them inside the swept disk. The coaxial shaft is the standard clock solution and removes both problems.

## Clearances

| Spec | Value |
|------|-------|
| Bar tip → dial underside (incl. runout) | **≥ 5 mm LOCKED** |
| Bar tip radius → enclosure inner wall | 80 → 85.5 (5.5 mm) |
| Hour hand length vs dial marker inner radius | 60 < 67 |
| Hour drive ratio | **1:1 LOCKED** (direct coupler) |
| Slip ring primary | SenRing **G012**: 5000 RPM, 5 A/circuit (verify on catalog PDF) |

## Sources

- Slip primary: https://www.senring.com/high-speed-slip-ring/g012-12.html — PDF https://www.senring.com/pdf/Senring-G012-12-Series-SlipRing-Catalog.pdf
- MagAlpha side-shaft mounting: MPS MA730 datasheet / app notes (verify achievable accuracy with the chosen ring magnet)
- DRV5023: https://www.ti.com/lit/ds/symlink/drv5023.pdf
