# LCSC / source links (hybrid v0.3)

Prefer JLCPCB assembly where footprints match. Verify stock before order.

| Part | Role | LCSC | Source |
|------|------|------|--------|
| ESP32-S3-WROOM-1-N16R8 | Base MCU | C2913202 | https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-S3-WROOM-1-N16R8_C2913202.html |
| ESP32-C3-MINI-1-N4 | Rotor MCU | C2934560 | https://www.lcsc.com/product-detail/WiFi-Modules_Espressif-Systems-ESP32-C3-MINI-1-N4_C2934560.html |
| DRV8313PWPR | Minute BLDC driver | C92482 | https://www.lcsc.com/product-detail/Motor-Drivers_Texas-Instruments-DRV8313PWPR_C92482.html |
| ULN2003ADR | Hour stepper driver | C7512 | https://www.lcsc.com/product-detail/Darlington-Transistor-Arrays_Texas-Instruments-ULN2003ADR_C7512.html |
| XL4015E1 | 5 V buck | C51661 | https://www.lcsc.com/product-detail/DC-DC-Converters_XLSEMI-XL4015E1_C51661.html |
| AMS1117-3.3 | 3V3 LDO (base) | C6186 | https://www.lcsc.com/product-detail/Low-Dropout-Regulators-LDO_Advanced-Monolithic-Systems-AMS1117-3-3_C6186.html |
| ME6211C33M5G-N | 3V3 LDO (rotor) | C235316 | https://www.lcsc.com/product-detail/Low-Dropout-Regulators-LDO_MICRONE-Nanjing-Micro-One-Elec-ME6211C33M5G-N_C235316.html |
| SN74AHCT125PWR | 5 V SPI buffer | C5947 | https://www.lcsc.com/product-detail/Buffer-Driver-Transceiver_Texas-Instruments-SN74AHCT125PWR_C5947.html |
| APA102-2020 | POV LEDs | C22439302 | https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_Worldsemi-APA102-2020_C22439302.html |
| SK9822 (alt LED) | Alt to APA102 | C2909059 | https://www.lcsc.com/product-detail/Light-Emitting-Diodes-LED_OPSCO-Optoelectronics-SK9822_C2909059.html |
| AH1806-W-7 | Hall index | C126663 | https://www.lcsc.com/product-detail/Hall-Sensor_Diodes-Incorporated-AH1806-W-7_C126663.html |
| SMAJ5.0A | 5 V TVS | C83329 | https://www.lcsc.com/product-detail/TVS_Littelfuse-SMAJ5-0A_C83329.html |
| AS5600 (module/IC) | Minute encoder | C970804 / breakout | https://www.lcsc.com/product-detail/Angle-Position-Sensors_AMS-AS5600-ASST_C970804.html |
| 28BYJ-48 + driver loom | Hour stepper | mech vendor | Common 5 V unipolar gear stepper (ULN2003 packs widely available) |
| Slip ring 2‑circuit | 5 V/GND to rotor | mech vendor | Choose continuous rating ≫ LED+MCU load (e.g. ≥2 A) |

Capacitors/resistors: generic 0603/0805 JLCPCB basic parts unless noted (C5 470 µF electrolytic on rotor).
