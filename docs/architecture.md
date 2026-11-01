# Clockor hybrid architecture (v0.3)

Jason chose **hybrid** hands after Chief Round 1: keep POV graphics simple while a normal clock still reads at a glance.

## Mechanical arrangement (simplest)

- **Minute = spinning POV bar** — one counterbalanced LED PCB (~150 mm, 36× APA102-2020) on a **solid shaft**, driven by a **2204/2205-class gimbal BLDC** (higher KV / ~12 V bus for ~600–1200 RPM). Hub clamp + balance trim pads on the bar tips. Clearance guard around the swept disk; firmware spin-down on fault.
- **Hour = slow physical hand** — **28BYJ-48** (or similar 5 V unipolar stepper) **front-mounted on the dial**, driven through a short stub; the POV bar spins **behind** the dial with axial clearance so the hour hand never intersects the rotor. No hollow coaxial tube, no second slip ring, no hour rotor PCB.
- **Static clock mode** — BLDC parks the bar at the minute angle with LEDs lit as a glowing minute hand; stepper tracks hour. **Graphics mode** — bar spins; hour hand can hold or creep slowly (non-critical).

## Electrical

| Board | Role | Key parts |
|-------|------|-----------|
| `base-controller` | Stationary MCU + power + motors | ESP32-S3-WROOM-1-N16R8, XL4015→5 V, AMS1117→3V3, **1× DRV8313** (minute BLDC), **ULN2003A** (hour stepper), USB-C + barrel |
| `hand-minute` | Rotor POV bar | ESP32-C3-MINI-1-N4, ME6211 3V3, 74AHCT125 level shift, 36× APA102, **AH1806-W** hall index, **≥470 µF** bulk + **SMAJ5.0A** TVS on 5 V |

**Removed vs coaxial two-hand:** `hand-hour` rotor board, second DRV8313, **TCA9548A** I²C mux.

### Buses and timing (Chief fixes)

1. **I²C** — S3 **I2C0 → AS5600** (minute shaft angle / park). **I2C1** on a header only (no mux).
2. **POV sync** — fixed magnet + **AH1806** once-per-rev on the rotor; C3 interpolates locally. **ESP-NOW** carries double-buffered frame payloads only (not bit-clock).
3. **Power transfer** — 2-circuit slip ring **5 V + GND** only, rated well above LED+MCU load; rotor **≥470 µF** + TVS; firmware **brightness cap**.
4. **SPI LEDs** — target **8–12 MHz** through 74AHCT125.
5. **ME6211** — 500 mA class; C3 Wi-Fi peaks ~300–350 mA OK with ceramic bulk (C2 22 µF on 3V3). Upsize LDO only if brown-outs appear.
6. **Buck** — XL4015 kept; TPS54560-class is an optional drop-in later if thermals/load demand it.
7. **Motor drive** — DRV8313 adequate for 2204-class; no DRV8316 / current-sense yet (open if torque margin fails).

## Data flow

```
[Phone/host or S3 UI] --ESP-NOW frames--> [C3 on bar] --SPI--> APA102 chain
                         ^
                         +-- hall IRQ index --> local POV phase

[S3] --SimpleFOC/PWM--> DRV8313 --> BLDC --> shaft + AS5600 (I2C0)
[S3] --GPIO--> ULN2003A --> 28BYJ-48 --> hour hand
[S3 5V] --slip--> bar 5V/GND
```

## Safety / balance (docs + firmware)

Trim pads (TP1–TP4), clamp hub, disk guard, max RPM limit, and forced spin-down on hall loss / over-current / mode exit — implement in firmware; mechanical guard is a hard requirement before spin tests.
