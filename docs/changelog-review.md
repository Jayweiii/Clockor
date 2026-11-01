# Design review changelog

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
