# Clockor hybrid architecture (v0.4 — Chief Round 2)

Jason chose **hybrid** hands: POV graphics stay simple; a normal clock still reads at a glance.

## Mechanical arrangement (Round 2 must-fix)

### Dial and axial clearance
- **Dial** = **clear acrylic / diffuser** (see-through face; hour markers etched or printed on the rear/front of the sheet).
- **Axial gap** from **POV bar tip plane to dial underside ≥ 5 mm**, including **hub runout** allowance. Do not shrink this stack in CAD without a measured runout budget.
- Only the **hour hand** sits in front of the dial. The spinning minute bar stays **behind** the dial.

### Minute = spinning POV bar
- Counterbalanced LED PCB (~150 mm, 36× APA102-2020) on a **solid minute shaft**.
- Drive: **Furitek KOMODO 2204 1400 KV, 12S14P (7 pole pairs)** on ~12 V bus → ~600–1200 RPM with SimpleFOC + AS5600 park.
- Hub clamp + balance trim pads (TP1–TP4). Clearance guard around the swept disk.

### Hour = slow physical hand (relocated)
- **28BYJ-48** (5 V unipolar) is **not** dial-front-mounted.
- Stepper sits **behind the motor / plate, off-axis**, driving a **thin hollow hour shaft** (tube around the minute shaft) via **gear or belt**.
- Only the thin hour hand (and optionally a short hub) appear in front of the clear dial. No hour rotor PCB, no second slip ring.

### Encoder / slip stack-up (locked)
Axial order (rear → front), see also `docs/stack-up.md`:

1. **AS5600** board + diametric magnet on the **motor shaft rear end**
2. **Furitek 2204** BLDC (stator to chassis)
3. Bearings / plate
4. **Mercotac 205** brushless slip ring on the **front shaft end** (or mid-stub with floating stator leads) — **not** through-bore; wires dress to hub
5. Hub clamp + `hand-minute` PCB
6. Clear acrylic dial (≥5 mm above bar tip incl. runout)
7. Hollow hour tube / hour hand in front of dial

**Static clock mode** — BLDC parks the bar at the minute angle with LEDs lit as a glowing minute hand; stepper tracks hour. **Graphics mode** — bar spins; hour hand holds or creeps slowly.

## Electrical

| Board | Role | Key parts |
|-------|------|-----------|
| `base-controller` | Stationary MCU + power + motors | ESP32-S3-WROOM-1-N16R8, XL4015→5 V, AMS1117→3V3, **1× DRV8313** (minute BLDC), **ULN2003A** (hour stepper), USB-C + barrel |
| `hand-minute` | Rotor POV bar | ESP32-C3-MINI-1-N4, ME6211 3V3, 74AHCT125 level shift, 36× APA102, **AH1806-W** hall index, **≥470 µF** bulk + **SMAJ5.0A** TVS on 5 V |

**Removed vs coaxial two-hand:** `hand-hour` rotor board, second DRV8313, **TCA9548A** I²C mux.

### Buses and timing

1. **I²C** — S3 **I2C0 → AS5600** (minute shaft angle / park). **I2C1** on a header only (no mux).
2. **POV sync** — fixed magnet + **AH1806** once-per-rev on the rotor; C3 interpolates locally. **ESP-NOW** carries double-buffered frame payloads only (not bit-clock).
3. **Power transfer** — Mercotac **205** (2× **4 A**, **2000 RPM** datasheet) for **5 V + GND**; rotor **≥470 µF** + TVS; firmware **~1.2 A LED current cap**.
4. **SPI LEDs** — target **8–12 MHz** through 74AHCT125.
5. **ME6211** — 500 mA class; C3 Wi-Fi peaks ~300–350 mA OK with ceramic bulk (C2 22 µF on 3V3).
6. **Buck** — XL4015 kept; TPS54560-class optional later.
7. **Motor drive** — DRV8313 for locked 2204; DRV8316 + sense only if torque margin fails.

## Data flow

```
[Phone/host or S3 UI] --ESP-NOW frames--> [C3 on bar] --SPI--> APA102 chain
                         ^
                         +-- hall IRQ index --> local POV phase

[S3] --SimpleFOC/PWM--> DRV8313 --> Furitek 2204 --> shaft
      AS5600 magnet @ shaft REAR (I2C0)
[S3] --GPIO half-step--> ULN2003A --> 28BYJ-48 (off-axis) --gear/belt--> hollow hour shaft
[S3 5V] --Mercotac 205--> bar 5V/GND
```

## Safety / firmware interlocks

See `docs/firmware-interlocks.md`: soft-start, spin-down on hall / ESP-NOW heartbeat loss, ~1.2 A LED cap, hour half-step + coil de-energize between moves. Mechanical disk guard is mandatory before spin tests.
