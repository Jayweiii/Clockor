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
