# Clockor hybrid architecture (v0.6 — redesign)

Hybrid hands: a **spinning POV bar** shows the minute (and graphics), a **slow
physical hour hand** reads at a glance. v0.6 keeps that concept and fixes the
v0.5 electrical bugs and the hour-drive layout. Full rationale:
`docs/design-review-v0.6.md`.

## Mechanical arrangement (coaxial)

Axial order, rear → front (`docs/stack-up.md`, `cad/build_assembly.py`):

1. **28BYJ-48** (5 V) at the rear, output shaft **on the clock axis**, body offset.
2. **Coupler** 5 mm → 3 mm, carries the **hour-home magnet** (hall on `J9`).
3. **Ring magnet** on the minute tube + **MA730** side-shaft encoder satellite (`J10`, SPI).
4. **Hollow-shaft gimbal BLDC** (2804 class, ~100 KV, 7 pole pairs) on the 24 V bus.
5. Base plate, two bearings on the **hollow minute tube** (Ø6/Ø4).
6. **SenRing G012** through-bore brush slip ring on the minute tube (5 V + GND).
7. Hub + `hand-minute` POV bar (160 mm overall, 36× APA102-2020, both sides of hub).
8. **≥ 5 mm** gap (incl. runout) to the **clear acrylic dial** (Ø5 mm centre hole).
9. **Hour hand** on the Ø3 mm **hour shaft**, which runs inside the minute tube on two MR63 bearings.

Only the hour hand is in front of the dial. v0.5 put the stepper, pulleys and
belt on the dial face, which covered the POV image.

**Static clock mode:** the BLDC parks the bar at the minute angle (lit as a
minute hand); the stepper tracks the hour. **Graphics mode:** the bar spins
600–1200 RPM, the hour hand holds.

## Electrical

| Board | Role | Key parts |
|-------|------|-----------|
| `base-controller` | Stationary MCU, power, motors | ESP32-S3-WROOM-1-N16R8, XL4015 24→5 V, AMS1117 3V3, DRV8313 (minute BLDC), ULN2003A (hour), USB-C sink + USBLC6 ESD, `J10` encoder SPI, `J9` hour home |
| `hand-minute` | Rotor POV bar | ESP32-C3-MINI-1-N4, ME6211, 74AHCT125, 36× APA102-2020, **DRV5023** index hall, 2× 330 µF polymer + SMAJ5.0A, `J2` UART programming header, USB pogo pads |

### Power

- **24 V** barrel input (`VIN_24V`) → DRV8313 VM directly; XL4015 → **+5 V**; AMS1117 → +3V3.
- 24 V is needed because a ~100 KV gimbal motor only reaches ~1200 RPM no-load on 12 V.
- **USB-C** is a proper sink: VBUS → SS34 → +5 V (logic-only bench power and flashing), 5.1 k Rd on CC1/CC2, USBLC6-2SC6 on D±. Motors need the barrel supply.
- Slip ring carries **+5 V / GND** to the rotor; the rotor has ≥ 660 µF bulk + TVS; firmware caps LED current at ~1.2 A.

### ESP32-S3 pin map (base)

| Function | GPIO | Pad | Note |
|---|---|---|---|
| M1_IN1/2/3 (PWM) | 3 / 4 / 5 | 15 / 4 / 5 | GPIO3 is a JTAG-source strap only if eFuse set |
| M1_EN_ALL (EN1–3) | 6 | 6 | 10 k pull-down: bridge off at reset |
| M1_nSLEEP (+nRESET) | 38 | 31 | 10 k pull-down: driver asleep at reset |
| M1_nFAULT | 18 | 11 | 10 k pull-up. **Moved off GPIO46** (strap) |
| HR_IN1–4 | 7 / 15 / 16 / 17 | 7–10 | ULN2003A |
| HR_HOME | 11 | 19 | 10 k pull-up + 100 nF |
| ENC SCK/MISO/MOSI/CS | 12 / 13 / 14 / 39 | 20 / 21 / 22 / 32 | MA730 on `J10` |
| I2C0 SDA/SCL | 8 / 9 | 12 / 17 | `J5` (AS5600 bench fallback) |
| I2C1 SDA/SCL | 1 / 2 | 39 / 38 | `J6` spare |
| USB D− / D+ | 19 / 20 | 13 / 14 | native USB-Serial-JTAG |
| STATUS_LED / MODE | 10 / 21 | 18 / 23 | |

GPIO35–37 are left free for the N16R8's octal PSRAM. GPIO45/46 are not connected, so their internal pull-downs set the boot mode.

### ESP32-C3 pin map (rotor)

| Function | GPIO | Note |
|---|---|---|
| LED data (→ AHCT125 → APA102 SDI) | 8 | strap: 10 k pull-up |
| LED clock (→ AHCT125 → APA102 CKI) | 4 | |
| HALL_IN (DRV5023) | 5 | 10 k pull-up |
| BOOT | 9 | button + `J2` pin 4 |
| UART0 TX / RX | 21 / 20 | `J2` pins 5 / 6 |
| USB D− / D+ | 18 / 19 | pogo pads TP5 / TP6 |
| GPIO2 | 2 | strap: 10 k pull-up |

## Buses and timing

1. **Minute angle**: MA730 (SPI) on the base S3. It provides absolute angle for parking and velocity for interlocks.
2. **POV phase**: DRV5023 on the rotor triggers once per revolution from a fixed magnet; the C3 interpolates. **ESP-NOW** carries frame payloads and heartbeats only.
3. **SPI LEDs**: 8–12 MHz through the 74AHCT125 (3.3 V → 5 V).
4. **Hour**: ULN2003A half-step, coils released between moves; 1:1 direct coupling; `HR_HOME` index.

## Data flow

```
[Phone/host or S3 UI] --ESP-NOW frames--> [C3 on bar] --SPI--> APA102 chain
                                             ^
                                             +-- DRV5023 index IRQ (POV phase)

[S3] --SimpleFOC PWM--> DRV8313 --> gimbal BLDC --> hollow minute tube --> bar
[S3] <--SPI-- MA730 (side-shaft, ring magnet on tube)
[S3] --half-step--> ULN2003A --> 28BYJ-48 --coupler--> Ø3 hour shaft --> hour hand
[S3] <--HR_HOME-- hall @ coupler magnet (J9)
[24 V] -> XL4015 -> 5 V --SenRing G012--> bar 5 V/GND
```

## Safety

See `docs/firmware-interlocks.md`. A polycarbonate guard over the swept disk is mandatory before spin tests. Use the brush slip ring; the Mercotac (mercury) alternative stays documented in `docs/lcsc_sources.md` but is not recommended.
