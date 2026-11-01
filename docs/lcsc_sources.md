# LCSC / source links (hybrid v0.4 — Round 2 locked mech)

Prefer JLCPCB assembly where footprints match. Verify stock before order.

## Locked mechanical (Round 2)

| Part | Role | Spec (verified) | Source |
|------|------|-----------------|--------|
| **Furitek KOMODO 2204 1400KV** | Minute BLDC | **12S14P** (7 pole pairs), 1400 KV, Ø28×19 mm, 180 W, max 15 A | https://furitek.com/products/furitek-2204-outrunner-1400kv-motor |
| **T-Motor MN2204-1400** (alt) | Same class alt | 1400 KV, 12N14P family — confirm pole count on lot label | Search “MN2204 1400KV” (T-Motor / distributors) |
| **Mercotac 205** | Slip ring 5 V/GND | **2 conductors, 4 A each, 2000 RPM** (datasheet); 250 VAC/VDC; brushless mercury | https://www.mercotac.com/html/205.html — catalog https://www.mercotac.com/data/pdf/MercotacProductCatalog.pdf |
| **Mercotac 205-H** (alt high RPM) | Same, 3600 RPM | If spin tests need more headroom | Same Mercotac 205 page (H suffix) |
| **Moflon MR204** (alt) | Mercury capsule | 2 pole × 4 A, **2000 RPM** | https://www.moflon.com/pdf/mr_catalog.pdf |
| 28BYJ-48 5 V | Hour stepper | Unipolar gear motor | Common packs; drive with onboard ULN2003A |
| Clear acrylic / diffuser dial | Face | Laser-cut clear or opal acrylic | Local plastics / Ponoko / SendCutSend |
| Diametric magnet for AS5600 | Encoder | Ø6×2.5 class diametric | AMS AS5600 magnet guide + vendor magnet |

**Mercotac notes:** Mount with **UP** marking correct; prefer near-vertical shaft. Not a through-bore — place on **front shaft end** per `docs/stack-up.md`. Commodity brush capsules (SenRing / generic 250–300 RPM) **do not** meet ≥1500 RPM — do not substitute without a datasheet speed check.

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
| AH1806-W-7 | Hall index | C126663 | https://www.lcsc.com/product-detail/Hall-Sensor_Diodes-Incorporated-AH1806-W-7_C126663.html |
| SMAJ5.0A | 5 V TVS | C83329 | https://www.lcsc.com/product-detail/TVS_Littelfuse-SMAJ5-0A_C83329.html |
| AS5600 (module/IC) | Minute encoder | C970804 / breakout | https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html |

Capacitors/resistors: generic 0603/0805 JLCPCB basic parts unless noted (C5 470 µF electrolytic on rotor).
