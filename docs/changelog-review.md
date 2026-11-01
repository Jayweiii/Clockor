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
