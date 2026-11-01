# Clockor hybrid architecture (v0.5 — Chief Round 3)

Jason chose **hybrid** hands: POV graphics stay simple; a normal clock still reads at a glance.

## Mechanical arrangement

### Dial and axial clearance
- **Dial** = **clear acrylic / diffuser** (see-through face; hour markers etched or printed).
- **Axial gap** from **POV bar tip plane to dial underside ≥ 5 mm**, including **hub runout** allowance.
- Only the **hour hand** (and its stub/drive plane) sits in front of the dial. The spinning minute bar stays **behind** the dial.

### Minute = spinning POV bar
- Counterbalanced LED PCB (~150 mm, 36× APA102-2020) on a **solid minute shaft**.
- Drive: **Furitek KOMODO 2204 1400 KV, 12S14P (7 pole pairs)** on ~12 V bus → ~600–1200 RPM with SimpleFOC + AS5600 park.
- Hub clamp + balance trim pads (TP1–TP4). Clearance guard around the swept disk.

### Hour = slow physical hand (Round 3 stub axle)
- **28BYJ-48** off-axis, **1:1** thin belt or spur gear.
- Hour hand on a **short stub axle** in a **small bearing at the acrylic dial center**.
- Entire hour drive is **in front of the bar sweep** (on / just behind the dial plane that already clears the bar). **No hollow tube** around the minute shaft.
- **Hour home:** AH1806 (+ magnet on stub) or optical flag → `HR_HOME` on base (U6 / J9).

### Encoder / slip stack-up
Axial order (rear → front), see `docs/stack-up.md`:

1. **AS5600** + diametric magnet on motor shaft **rear**
2. **Furitek 2204** BLDC
3. Bearings / plate
4. **SenRing G012** brush slip (primary) on **front** shaft — Mercotac 205 alt only
5. Hub clamp + `hand-minute` PCB
6. Clear acrylic dial (≥5 mm above bar tip incl. runout)
7. Hour stub bearing + hand + 1:1 drive (front of dial / bar sweep)

**Static clock mode** — BLDC parks the bar at the minute angle with LEDs lit as a glowing minute hand; stepper tracks hour. **Graphics mode** — bar spins; hour hand holds or creeps slowly.

## Electrical

| Board | Role | Key parts |
|-------|------|-----------|
| `base-controller` | Stationary MCU + power + motors | ESP32-S3-WROOM-1-N16R8, XL4015→5 V, AMS1117→3V3, **1× DRV8313**, **ULN2003A**, **AH1806 hour home (U6) + J9**, USB-C + barrel |
| `hand-minute` | Rotor POV bar | ESP32-C3-MINI-1-N4, ME6211 3V3, 74AHCT125, 36× APA102, **AH1806** rotor index, **≥470 µF** + **SMAJ5.0A** |

### Buses and timing

1. **I²C** — S3 **I2C0 → AS5600**. **I2C1** header only.
2. **POV sync** — rotor **AH1806** once-per-rev; C3 interpolates. **ESP-NOW** = frame payloads only.
3. **Power transfer** — **SenRing G012** primary (5 A, 5000 RPM) for **5 V + GND**; Mercotac 205 alt; rotor **≥470 µF** + TVS; firmware **~1.2 A LED cap**.
4. **SPI LEDs** — **8–12 MHz** through 74AHCT125.
5. **Hour** — ULN2003A half-step + coil de-energize; **1:1** stub drive; **HR_HOME** hall.

## Data flow

```
[Phone/host or S3 UI] --ESP-NOW frames--> [C3 on bar] --SPI--> APA102 chain
                         ^
                         +-- hall IRQ index --> local POV phase

[S3] --SimpleFOC/PWM--> DRV8313 --> Furitek 2204 --> solid minute shaft
      AS5600 magnet @ shaft REAR (I2C0)
[S3] --GPIO half-step--> ULN2003A --> 28BYJ-48 --1:1 belt/gear--> dial stub + hour hand
[S3] <--HR_HOME-- AH1806 @ dial stub
[S3 5V] --SenRing G012 (Mercotac 205 alt)--> bar 5V/GND
```

## Safety / firmware interlocks

See `docs/firmware-interlocks.md`. Mechanical disk guard mandatory before spin tests. Prefer brush slip to avoid mercury handling; if Mercotac alt is used, follow orientation + hazardous disposal notes in `docs/lcsc_sources.md`.
