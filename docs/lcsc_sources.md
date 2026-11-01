# LCSC / source links (hybrid v0.5 — Round 3)

Prefer JLCPCB assembly where footprints match. Verify stock before order.

## Locked mechanical (Round 3)

| Part | Role | Spec (verified) | Source |
|------|------|-----------------|--------|
| **Furitek KOMODO 2204 1400KV** | Minute BLDC | **12S14P** (7 pole pairs), 1400 KV, Ø28×19 mm, 180 W, max 15 A | https://furitek.com/products/furitek-2204-outrunner-1400kv-motor |
| **T-Motor MN2204-1400** (alt) | Same class alt | 1400 KV, 12N14P family — confirm pole count on lot label | Search “MN2204 1400KV” |
| **SenRing G012-06 / G012-12 (PRIMARY)** | Brush through-bore slip | **≥5000 RPM**, **5 A/circuit**, ID **12.7 mm**, precision brush — meets ≥2000 RPM / ≥2 A | Product https://www.senring.com/high-speed-slip-ring/g012-12.html — **datasheet PDF** https://www.senring.com/pdf/Senring-G012-12-Series-SlipRing-Catalog.pdf |
| **Mercotac 205 (ALT only)** | Mercury capsule slip | 2 conductors, **4 A**, **2000 RPM**; brushless mercury | https://www.mercotac.com/html/205.html — catalog https://www.mercotac.com/data/pdf/MercotacProductCatalog.pdf |
| **Mercotac 205-H** (alt high RPM) | Same, 3600 RPM | Only if mercury path re-selected | Same Mercotac 205 page (H suffix) |
| 28BYJ-48 5 V | Hour stepper | Unipolar; **1:1** belt/gear to dial stub | Common packs; ULN2003A |
| Dial-center flange bearing | Hour stub | Small thin-section / flanged (e.g. F695 / MR85 class ESTIMATE) | Bearing supplier — match stub OD |
| Clear acrylic / diffuser dial | Face | Laser-cut | Local plastics / Ponoko / SendCutSend |
| Diametric magnet (AS5600) | Minute encoder | Ø6×2.5 class diametric | AMS guide + vendor |
| Hour-home magnet | Stub index | Small NdFeB on stub | Vendor |

### Slip ring choice (Round 3)

**Primary = SenRing G012 brush** (simplicity / safety preference over mercury):

- Linked catalog PDF confirms **5000 RPM** and **5 A** per circuit — above the ≥2000 RPM / ≥2 A bar.
- Through-bore ID 12.7 mm: use a collar / adapter on the Ø5 minute shaft (or select mating shaft stub).
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
| SK9822 (alt LED) | Alt to APA102 | C2909059 | https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_OPSCO-Optoelectronics-SK9822_C2909059.html |
| AH1806-W-7 | Hall (rotor index + **hour home U6**) | C126663 | https://www.lcsc.com/product-detail/Hall-Sensor_Diodes-Incorporated-AH1806-W-7_C126663.html |
| SMAJ5.0A | 5 V TVS | C83329 | https://www.lcsc.com/product-detail/TVS_Littelfuse-SMAJ5-0A_C83329.html |
| AS5600 (module/IC) | Minute encoder | C970804 / breakout | https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html |

Capacitors/resistors: generic 0603/0805 JLCPCB basic parts unless noted (C5 470 µF electrolytic on rotor).
