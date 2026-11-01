# Mechanical stack-up (hybrid v0.5 — Round 3)

All lengths in mm. Values marked **ESTIMATE** pending measured parts; **LOCKED** dimensions carry forward from Round 2 / Round 3.

## Axial order (rear → front, +Z toward dial)

| # | Element | Notes |
|---|---------|--------|
| 1 | AS5600 breakout + diametric magnet | Magnet on **motor shaft rear end**; air gap ~0.5–1.5 mm per AMS AS5600 app note |
| 2 | Furitek KOMODO 2204 (Ø28×19) | Stator fixed to chassis; **solid minute shaft** through |
| 3 | Rear bearing / motor plate | |
| 4 | Base plate / enclosure floor | ESP32-S3, DRV8313, ULN2003A, buck; hour stepper may sit here **or** on dial plate (see hour path) |
| 5 | Front bearing | |
| 6 | **Slip ring (primary: SenRing G012 brush)** | On **front shaft end** (through-bore ID 12.7 mm class — or collar adapter on Ø5 shaft). Stator → J7; rotor → hub. Mercotac 205 remains **alt** only |
| 7 | Hub clamp + `hand-minute` PCB | Balanced bar; LEDs both sides of hub |
| 8 | **Air gap ≥ 5 mm LOCKED** | Bar tip / LED top plane → dial underside, **including hub runout** |
| 9 | Clear acrylic / diffuser dial | Markers on dial; see-through |
| 10 | **Hour stub axle + hand (front of dial only)** | Short stub in small dial-center bearing; **no hollow tube** around minute shaft |

## Hour drive (Round 3 — stub axle, 1:1, entirely in front of bar sweep)

```
                    [acrylic dial]
                          |
     [small flange bearing at dial center]
                          |
              [short stub axle] ---- hour hand
                          |
              [1:1 pulley / thin gear]
                          |
         thin GT2 belt or 1:1 spur  (plane is IN FRONT of dial,
                                    which is already in front of bar)
                          |
              [28BYJ-48 pulley]   stepper body may sit on dial rear
                                  plate / bezel — still off-axis;
                                  drive plane does NOT enter bar sweep
```

**Rules (LOCKED Round 3):**
- Hour hand rides a **short stub axle** in a **small bearing at the acrylic dial center**.
- Drive is **1:1** (belt or gear) from an **off-axis 28BYJ-48**.
- Entire hour mechanism (stub, bearing, pulleys, belt/gear, stepper shaft) is **in front of the POV bar sweep** — typically on / immediately behind the dial face plane that already clears the bar by ≥5 mm. Nothing concentric with the minute shaft behind the dial.
- Minute shaft stays **solid** and independent; it does **not** carry a hollow hour tube.

**Home:** small magnet on the hour stub + **AH1806** (U6 / J9 on `base-controller`) or optical flag — once-per-rev hour index for firmware.

## Clearances (LOCKED / target)

| Spec | Value |
|------|-------|
| Bar tip → dial underside (incl. runout) | **≥ 5 mm LOCKED** |
| Dial material | Clear acrylic or diffuser sheet |
| Hub radial runout allowance in gap budget | Include measured TIR |
| Hour drive ratio | **1:1 LOCKED** |
| Slip ring primary (brush) | SenRing **G012** series — **5000 RPM**, **5 A/circuit**, linked catalog PDF |
| Slip ring alt (mercury) | Mercotac **205** — **2000 RPM**, **4 A/circuit**; orientation + Hg notes in `docs/lcsc_sources.md` |

## Sources

- Motor: https://furitek.com/products/furitek-2204-outrunner-1400kv-motor
- Slip primary: https://www.senring.com/high-speed-slip-ring/g012-12.html — PDF https://www.senring.com/pdf/Senring-G012-12-Series-SlipRing-Catalog.pdf
- Slip alt: https://www.mercotac.com/html/205.html
- AS5600: https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html
- Hour home hall: https://www.lcsc.com/product-detail/Hall-Sensor_Diodes-Incorporated-AH1806-W-7_C126663.html
