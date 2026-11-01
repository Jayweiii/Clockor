# Mechanical stack-up (hybrid v0.4)

All lengths in mm. Values marked **ESTIMATE** pending measured parts; **LOCKED** dimensions are Round 2 must-fix.

## Axial order (rear → front, +Z toward dial)

| # | Element | Notes |
|---|---------|--------|
| 1 | AS5600 breakout + diametric magnet | Magnet on **motor shaft rear end**; air gap ~0.5–1.5 mm per AMS AS5600 app note |
| 2 | Furitek KOMODO 2204 (Ø28×19) | Stator fixed to chassis; shaft through |
| 3 | Rear bearing / motor plate | |
| 4 | Base plate / enclosure floor | ESP32-S3, DRV8313, ULN2003A, buck |
| 5 | Front bearing | |
| 6 | Mercotac 205 slip ring | On **front shaft end** (capsule, not through-bore). Stator leads → J7; rotor leads → hub. Mount **UP** per Mercotac (vertical preferred). Datasheet **2000 RPM / 4 A/circuit** |
| 7 | Hub clamp + `hand-minute` PCB | Balanced bar; LEDs both sides of hub |
| 8 | **Air gap ≥ 5 mm LOCKED** | Bar tip / LED top plane → dial underside, **including hub runout** |
| 9 | Clear acrylic / diffuser dial | Markers on dial; see-through |
| 10 | Thin hollow hour tube + hour hand | Tube concentric around minute shaft; **only hand in front of dial** |

## Hour drive (off-axis)

```
[28BYJ-48 behind plate] --gear or GT2 belt--> [hour pulley on hollow tube]
                                              |
                                         tube slips over minute shaft
                                              |
                                         hour hand in front of dial
```

Minute shaft is solid and independent. Hour tube never carries the POV bar.

## Clearances (LOCKED / target)

| Spec | Value |
|------|-------|
| Bar tip → dial underside (incl. runout) | **≥ 5 mm LOCKED** |
| Dial material | Clear acrylic or diffuser sheet |
| Hub radial runout allowance in gap budget | Include measured TIR; do not consume the full 5 mm with CAD-nominal alone |
| Mercotac speed rating used | **2000 RPM** (datasheet) vs target spin ≤1200 RPM |
| Mercotac current | **4 A/circuit** vs firmware LED cap ~1.2 A |

## Sources

- Motor: https://furitek.com/products/furitek-2204-outrunner-1400kv-motor
- Slip ring: https://www.mercotac.com/html/205.html
- AS5600: https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html
