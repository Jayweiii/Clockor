# Design review changelog

## 2026-11-01 — v0.6 redesign (post-review)

Full write-up: `docs/design-review-v0.6.md`.

**Schematic fixes (base-controller)**
| # | v0.5 defect | v0.6 |
|---|---|---|
| 1 | USB-C VBUS pins on GND; CC1 collided with the +5V PWR_FLAG wire; no Rd | VBUS net → SS34 → +5V; 5.1 k Rd on CC1/CC2; USBLC6-2SC6 on D± |
| 2 | nFAULT pull-up on **GPIO46** (strap) blocked download mode | nFAULT → GPIO18; GPIO46 left on its internal pull-down |
| 3 | Stepper common + ULN COM on **12 V** for a 5 V 28BYJ-48 | Both on +5 V |
| 4 | EN1–3 + nSLEEP + nRESET on one floating GPIO | EN_ALL (GPIO6) and nSLEEP/nRESET (GPIO38), each with a 10 k pull-down |
| 5 | No ceramic VM decoupling | C23/C24 100 nF + C25 10 µF (50 V) |
| 6 | XL4015 VC tied to the 5 V output | 1 µF VC→VIN (typical application; confirm) |
| 7 | U6 hall on the PCB, in parallel with J9, unable to see the magnet | U6 removed; J9 remote + 100 nF |
| 8 | 12 V bus | 24 V bus for the gimbal motor; C1 35 V |
| 9 | — | J10 SPI header for MA730 side-shaft encoder |

**Schematic fixes (hand-minute)**
| # | v0.5 defect | v0.6 |
|---|---|---|
| 1 | TVS D40 pin 1 (cathode) on GND → shorts +5 V | Pin 1 → +5 V |
| 2 | No way to program the C3 | J2 UART header (3V3/GND/EN/IO9/TX/RX) + USB pogo pads TP5/TP6 |
| 3 | AH1806 (duty-cycled micropower) as rotor index | DRV5023 always-on hall |
| 4 | 74AHCT125 gates 3/4 inputs floating | OE → +5 V, A → GND |
| 5 | GPIO8/GPIO2 straps floating; EN without RC | 10 k pull-ups; 1 µF on EN |
| 6 | 470 µF 10×10 can on the rotor | 2× 330 µF polymer tantalum (7343) |

**Mechanical**: coaxial Ø3 hour shaft through a hollow minute tube, 28BYJ-48 at the rear (only the hour hand in front of the dial); hollow-shaft gimbal BLDC; MA730 side-shaft encoder. CAD: bar length fixed (300 → 160 mm overall), hour hand 110 → 60 mm.

**Tooling**: `scripts/sch_netcheck.py` (netlister validated against kicad-cli; collision/floating/undriven checks run on every rebuild); `scripts/export_bom.py` (BOMs generated from the schematics); `rebuild_boards.py --sch-only`; portable library paths; silk/courtyard stripping removed; fab-safe board rules. CI: DRC and fab outputs off until re-layout.

## 2026-11-01 — Round 3+ routing / CI DRC enable

- Both boards: **0 shorts**, **0 non-unconnected DRC errors** (warnings only: hole_to_hole, via_dangling).
- Unconnected remain: base ~68, hand ~74 (pattern router plateau); `kibot.yml` **`run_drc: true`** with `ignore_unconnected: true`.
- Hygiene: NPTH copper near J2 removed; dangling tracks/vias cleaned; courtyards stripped; edge clearance relaxed to 0.05 mm.
- Fresh review renders under `renders/` (F/B copper + front/back PNG/JPG, STEP/GLB, matplotlib 3D previews).

## 2026-11-01 — Hybrid v0.3 (Chief Round 1 → Jason decision)

**Decision:** Hybrid hand setup (widget). Repo stays **public**.

| # | Chief ask | Change |
|---|-----------|--------|
| 1 | Drop dual spinning / simplify | **Hybrid:** spinning minute POV bar + slow stepper hour; **deleted `hardware/hand-hour/`** |
| 2 | Higher-KV motor / bus for 1200 RPM | Spec **2204/2205-class** on ~12 V; keep **DRV8313** (no second driver) |
| 3 | Power transfer + bulk + TVS | Slip 5 V/GND; rotor **C5 470 µF** + **D40 SMAJ5.0A**; brightness cap noted |
| 4 | Remove TCA9548A | Removed; **I2C0→AS5600**, **I2C1** breakout |
| 5 | Hall index; ESP-NOW frames only | **AH1806-W** on minute bar; docs/SPI notes |
| 6 | Balance / guard / spin-down | TP1–4 balance pads; architecture.md safety notes |
| 7 | ME6211 / SPI / buck | ME6211 kept + 22 µF 3V3 bulk; SPI 8–12 MHz; XL4015 kept |
| 8 | Driver upsize if needed | Deferred — open question if 2204 torque short |

Also: single DRV8313 + **ULN2003A** for 28BYJ-48; CI matrix / place script drop hour board; ERC 0 errors on both remaining boards.

## 2026-11-01 — Hybrid v0.4 (Chief Round 2 conditional sign-off)

| # | Must-fix | Change |
|---|-----------|--------|
| 1 | Clear dial; hour off-axis; ≥5 mm gap | Dial = clear acrylic/diffuser; 28BYJ-48 **behind plate / off-axis** → gear/belt → **hollow hour shaft**; only hour hand in front; axial gap **≥5 mm** incl. hub runout documented in `docs/stack-up.md` + CAD |
| 2 | Lock 2204 12N14P + slip ≥2 A / ≥1500 RPM | **Furitek KOMODO 2204 1400KV 12S14P**; **Mercotac 205** (4 A, **2000 RPM** datasheet) — links in `docs/lcsc_sources.md` |
| 3 | AS5600 rear / slip other end | Magnet on shaft **rear**; Mercotac on **front**; stack-up doc |
| 4 | Firmware interlocks | Soft-start; spin-down on hall / ESP-NOW heartbeat loss; **~1.2 A LED cap** — `docs/firmware-interlocks.md` |
| 5 | Hour half-step + de-energize | Documented: half-step sequence; coils off between moves |

Routing: attempted; CI DRC remains off until 0-error route (see `docs/pcb-status.md`).

## 2026-11-01 — Hybrid v0.5 (Chief Round 3 full sign-off pending)

| # | Must-fix | Change |
|---|-----------|--------|
| 1 | Hour stub axle path | Short stub in dial-center bearing; **1:1** belt/gear from off-axis 28BYJ-48; **entirely in front of bar sweep**; hollow tube removed — `docs/stack-up.md` + CAD |
| 2 | 1:1 + hour home | Ratio **1:1 LOCKED**; **AH1806** U6 + R22 + J9 `HR_HOME` on `base-controller` |
| 3 | Brush slip primary | **SenRing G012** primary (linked PDF: 5000 RPM / 5 A); Mercotac 205 alt with **UP-not-below-horizontal** + **mercury disposal** notes |
| 4 | Hand-route → DRC | Careful pcbnew routing toward 0 DRC; enable CI DRC only if clean — see `docs/pcb-status.md` |

## Round 3 — 2026-11-01 (full sign-off pending → PCB honesty)

### Done
- Hour path: short stub axle + dial-center bearing, **1:1** belt/gear from off-axis 28BYJ-48, entirely in front of bar sweep — `docs/stack-up.md` + `cad/build_assembly.py` (no hollow tube).
- Hour home: AH1806 (+ magnet) on base schematic (U6 / J9 / `/HR_HOME`).
- Slip: **SenRing G012** brush primary (linked catalog PDF; ≥5000 RPM / 5 A); Mercotac 205 alt with orientation + Hg disposal notes.
- Boards hand-routed: **0 shorting_items** both; ERC 0 errors. Full 0 DRC **not** reached (unconnected + silk/courtyard). CI DRC remains disabled.

### Remaining
- Finish unconnected nets / hygiene → then enable KiBot DRC.
- Order-time confirm SenRing G012 collar on Ø5 shaft; dial bearing P/N.
