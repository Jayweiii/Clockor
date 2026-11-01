# LCSC / source links (hybrid v0.6)

Prefer JLCPCB assembly where footprints match. Verify stock before order.

## Mechanical (v0.6)

| Part | Role | Spec | Source |
|------|------|------|--------|
| **Hollow-shaft gimbal BLDC, 2804 class ~100 KV** (e.g. iPower GM2804H-100T) | Minute drive | 7 pole pairs (12N14P); **hollow shaft** passes the Ø3 hour shaft; ~2400 RPM no-load at 24 V | ESTIMATE — confirm bore and KV on the purchased lot |
| ~~Furitek KOMODO 2204 1400KV~~ | v0.5 minute BLDC | Replaced: 1400 KV runs at ~7 % of its speed range, solid shaft blocks the coaxial hour shaft | — |
| **SenRing G012-06 / G012-12 (PRIMARY)** | Brush through-bore slip ring | **≥5000 RPM**, **5 A/circuit**, ID **12.7 mm** → collar on the Ø6 minute tube | Product https://www.senring.com/high-speed-slip-ring/g012-12.html — **datasheet PDF** https://www.senring.com/pdf/Senring-G012-12-Series-SlipRing-Catalog.pdf |
| **Mercotac 205 (ALT, not recommended)** | Mercury capsule slip | 2 conductors, **4 A**, **2000 RPM**; it's an end-of-shaft part, so it doesn't fit the v0.6 coaxial shaft | https://www.mercotac.com/html/205.html |
| 28BYJ-48 **5 V** | Hour stepper | Unipolar; **coaxial at rear**, direct 5→3 mm coupler, 1:1 | Common packs |
| MR63ZZ (3×6×2.5) ×2 | Hour shaft inside minute tube | | Bearing supplier |
| Ø6/Ø4 tube + Ø3 ground shaft | Minute tube / hour shaft | ESTIMATE | |
| MagAlpha **MA730** satellite + diametric ring magnet (OD 12 / ID 6) | Minute absolute angle, side-shaft | SPI on `J10` | MPS; verify side-shaft accuracy |
| Hour-home hall + Ø2×1 magnet | `J9` | Slow index: a micropower AH1806 is fine here | |
| Clear acrylic dial, Ø5 centre hole | Face | Laser-cut | Local plastics / Ponoko / SendCutSend |
| 24 V ≥ 2 A PSU, 5.5×2.1 barrel | System supply | | |

### Slip ring choice

**Primary = SenRing G012 brush** (simplicity / safety preference over mercury):

- Linked catalog PDF confirms **5000 RPM** and **5 A** per circuit — above the ≥2000 RPM / ≥2 A bar.
- Through-bore ID 12.7 mm: use a collar on the Ø6 minute tube. The through-bore is what lets the coaxial hour shaft pass.
- G012-06 (6 circuits) or G012-12 (12 circuits) — only **2** used for 5 V + GND; spare circuits unused / reserved.

**Alt = Mercotac 205** (keep for noise / life comparison only):

- **Orientation limit (datasheet):** the unit’s **UP arrow must not point below horizontal**. Vertical preferred; a nearly horizontal desk-clock shaft is at the edge of the allowed attitude — validate life or use a short vertical stub / 205-SS if mercury is re-selected.
- **Mercury safety / disposal:** Mercotac contains **elemental mercury**. Do **not** open, crush, solder the capsule, or dispose in household trash. Treat as hazardous waste per local regulations (US: often universal-waste / HHM programs). Prefer the brush primary for builds that want to avoid Hg handling entirely.
- Commodity brush capsules rated **250–300 RPM** are **rejected** (below spin target).

## PCB / electrical (LCSC)

| Part | Role | LCSC | Source |
|------|------|------|--------|
| ESP32-S3-WROOM-1-N16R8 | Base MCU | C2913202 | https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N16R8_C2913202.html |
| ESP32-C3-MINI-1-N4 | Rotor MCU | C2934560 | https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-C3-MINI-1-N4_C2934560.html |
| DRV8313PWPR | Minute BLDC driver | C92482 | https://www.lcsc.com/product-detail/Motor-Drivers_Texas-Instruments-DRV8313PWPR_C92482.html |
| ULN2003ADR | Hour stepper driver | C7512 | https://www.lcsc.com/product-detail/Darlington-Transistor-Arrays_Texas-Instruments-ULN2003ADR_C7512.html |
| XL4015E1 | 5 V buck | C51661 | https://www.lcsc.com/product-detail/DC-DC-Converters_XLSEMI-XL4015E1_C51661.html |
| AMS1117-3.3 | 3V3 LDO (base) | C6186 | https://www.lcsc.com/product-detail/Low-Dropout-Regulators-LDO_Advanced-Monolithic-Systems-AMS1117-3-3_C6186.html |
| ME6211C33M5G-N | 3V3 LDO (rotor) | C235316 | https://www.lcsc.com/product-detail/Low-Dropout-Regulators-LDO_MICRONE-Nanjing-Micro-One-Elec-ME6211C33M5G-N_C235316.html |
| SN74AHCT125PWR | 5 V SPI buffer | C5947 | https://www.lcsc.com/product-detail/Buffer-Driver-Transceiver_Texas-Instruments-SN74AHCT125PWR_C5947.html |
| APA102-2020 | POV LEDs | C22439302 | https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_Worldsemi-APA102-2020_C22439302.html |
| SK9822 (alt LED) | **Not for POV**: its ~4.7 kHz PWM is slower than one display column | C2909059 | https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_OPSCO-Optoelectronics-SK9822_C2909059.html |
| **DRV5023FAQDBZR** | Rotor index hall (always-on, ~30 kHz sampling, open-drain) | verify | https://www.ti.com/lit/ds/symlink/drv5023.pdf |
| AH1806-W-7 | Off-board hour-home hall only (micropower; samples too slowly for the rotor index) | C126663 | https://www.lcsc.com/product-detail/Hall-Sensor_Diodes-Incorporated-AH1806-W-7_C126663.html |
| USBLC6-2SC6 | USB D± ESD (base) | verify | ST |
| SS34 | VBUS → +5 V OR-ing (base) | verify | |
| 330 µF 10 V polymer tantalum, 7343 (e.g. KEMET T520D) ×2 | Rotor bulk (replaces 470 µF can) | verify | KEMET |
| MA730GQ | Minute encoder (satellite) | verify | MPS |
| SMAJ5.0A | 5 V TVS | C83329 | https://www.lcsc.com/product-detail/TVS_Littelfuse-SMAJ5-0A_C83329.html |
| AS5600 (module/IC) | Bench fallback on `J5` only (needs a free shaft end) | C970804 / breakout | https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html |

Capacitors/resistors: generic 0603/0805 JLCPCB basic parts unless noted. Base C1 must be rated **≥ 35 V** (24 V bus); C23/C24/C25 **50 V**.

LCSC ids marked *verify* were not checked against live stock for this revision; `scripts/export_bom.py` leaves them blank in the CSVs on purpose.
