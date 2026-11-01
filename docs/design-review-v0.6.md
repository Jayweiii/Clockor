# Clockor design review — v0.5 → v0.6

**Date:** 2026-11-01 · **Scope:** both schematics, mechanical stack-up, PCB layouts, CI, docs · **Branch:** `claude/clockor-project-review-127y9z`

## 1. Verdict

The v0.5 concept is sound: a spinning POV bar for the minute and graphics, a physical hour hand, and a slip ring for rotor power. The implementation was **not buildable**. Five schematic defects would each have killed a board on first power-up or first flash. The front-mounted hour drive covered the display it was meant to sit beside. The PCBs passed DRC only because the checks had been switched off.

v0.6 fixes every schematic defect at the source (`scripts/rebuild_boards.py`), adds an automatic connectivity check so this class of bug can't recur silently, and moves the hour drive to a coaxial shaft. **The boards still need re-layout before ordering.**

| Area | v0.5 | v0.6 |
|---|---|---|
| Base schematic | 4 blocking defects | Fixed, 0 netcheck problems |
| Rotor schematic | 3 blocking defects | Fixed, 0 netcheck problems |
| Hour drive | Stepper + belt on the dial face | Coaxial shaft, only the hand in front |
| Minute motor | 1400 KV solid shaft, 12 V | ~100 KV hollow-shaft gimbal, 24 V |
| PCB | Routed, ~70 unconnected/board, silk & courtyards deleted | Stale, re-layout required |
| CI | DRC "passing" with unconnected ignored | ERC + docs only until layout is real |

## 2. Blocking defects found in v0.5 (all fixed)

Found by reading the KiCad netlists (`review/*.net`) and confirmed with `scripts/sch_netcheck.py`. The netlister reproduces kicad-cli's netlists exactly.

| # | Board | Defect | Consequence | v0.6 fix |
|---|---|---|---|---|
| B1 | base | USB-C **VBUS pins on GND**; CC1 on +5 V because the +5 V PWR_FLAG wire ended exactly on the CC1 pin tip; no 5.1 k Rd | Plugging in USB shorts the host's 5 V; C-to-C hosts never enable VBUS | VBUS net; Rd on both CC; USBLC6 ESD; VBUS→SS34→+5 V |
| B2 | base | DRV8313 nFAULT (10 k pull-up) on **GPIO46**, a boot strap | BOOT + GPIO46 high is an invalid boot mode, and USB is also dead (B1), so the board can't be flashed | nFAULT → GPIO18 |
| B3 | rotor | ESP32-C3 USB (GPIO18/19) and UART0 (GPIO20/21) **all unconnected** | No way to load the first firmware onto the spinning board | J2 UART header + USB pogo pads |
| B4 | rotor | TVS D40 **pin 1 = cathode on GND**, anode on +5 V (KiCad symbol pin 1 = `D_SMA` pad 1 = band) | Forward-biased diode across the rotor rail: a dead short | Pin 1 → +5 V |
| B5 | base | 28BYJ-48 common and ULN2003 COM on the **12 V** input; the motor is the 5 V version | ~5.8× rated coil power; the motor cooks | Both on +5 V |
| B6 | rotor | **AH1806** rotor index: a micropower hall that samples periodically. At 1200 RPM the magnet passes in ~1 ms | The index pulse is mostly missed, breaking POV phase lock and the "hall loss" interlock | DRV5023 always-on hall (~30 kHz) |

## 3. Should-fix issues (fixed)

- **Driver boot state:** EN1–3, nSLEEP and nRESET were tied to one GPIO with no pull, so the bridge could twitch during boot. Now EN_ALL and nSLEEP/nRESET are separate GPIOs, each with a 10 k pull-down.
- **VM decoupling:** only the shared 470 µF can. Added 2× 100 nF at the VM pins + 10 µF, all 50 V.
- **XL4015 VC** was tied to the 5 V output. It now has 1 µF from VC to VIN, per the typical application. *I couldn't fetch the datasheet here, so confirm before layout.*
- **Hour-home U6** sat on the base PCB, where it can't see a magnet on the hour shaft, and was wired in parallel with J9. Removed; J9 is the remote sensor input with a 100 nF filter.
- **Rotor:** floating 74AHCT125 inputs tied off; GPIO8/GPIO2 strap pull-ups; 1 µF EN delay.
- **Rotor bulk:** a 10×10 electrolytic can under up to ~130 g is replaced by 2× 330 µF polymer tantalum (7343), which is low profile with no wet electrolyte.
- **Schematic hygiene:** the BOOT and MODE button pins overlapped (0.16 mm apart), and the rotor's LED grid had 120 stub overlaps. KiCad didn't join them, but one stray junction would. The grid is now spaced and the check fails the build if this recurs.

## 4. Mechanical redesign

**Problem.** Round 3 put the 28BYJ-48, two pulleys and a belt on the dial face (CAD: stepper at x = 48 mm, Z = dial + 2 mm). The bar sweeps r ≤ 80 mm behind a **clear** dial, so the hour mechanism sat over the POV image. Moving it behind the dial would put it inside the swept disk.

**Fix: the standard clock arrangement.** A Ø3 hour shaft runs inside a hollow minute tube (two MR63 bearings), through the bar hub and a Ø5 hole in the dial. The 28BYJ-48 sits at the very rear, output shaft on the axis, with a direct 1:1 coupler. This change drives the other mechanical choices:

- **Motor:** the minute motor must pass the hour shaft, so a **hollow-shaft gimbal BLDC** (2804 class, ~100 KV) replaces the Furitek 2204 1400 KV. That's also a better electrical match: 1400 KV × 12 V ≈ 16,800 RPM no-load, so 1200 RPM used ~7 % of its range with almost no torque per amp. A 100 KV motor needs **24 V** to reach ~2400 RPM no-load, so the bus moves to 24 V (DRV8313 VM ≤ 60 V, XL4015 ≤ 36 V).
- **Encoder:** the rear shaft end is now the hour shaft, so AS5600 end-of-shaft sensing is impossible. **MA730 side-shaft** reads a ring magnet on the minute tube over SPI (`J10`). AS5600 stays on `J5` as a bench fallback.
- **Slip ring:** the SenRing G012's 12.7 mm through-bore now earns its keep, since the tube passes through it. The Mercotac (end-of-shaft, mercury) no longer fits.
- **Hour home:** magnet on the coupler; any hall on `J9`. The AH1806 is fine here because the hour index is slow.

The CAD (`cad/build_assembly.py`) is rebuilt to match. It also fixes two drawing bugs: the bar was drawn 150 mm *per side* (300 mm overall, outside the 180 mm enclosure), and the hour hand (110 mm) was longer than the dial radius.

## 5. PCB layouts

Not reusable. The v0.5 copper implements the defective netlist: VBUS is routed to GND and the TVS is reversed. About 70 nets per board are unrouted. Silkscreen and courtyards were deleted by the routing scripts, rules were loosened to hole clearance 0 / edge 0.05 mm, and stacked GND vias sit 0.2 mm apart. v0.6 restores fab-safe rules, stops the scripts deleting silk and courtyards, and disables DRC and fab outputs in CI so stale Gerbers can't be ordered. Re-layout procedure: `docs/pcb-status.md`.

## 6. Firmware notes

`docs/firmware-interlocks.md` is updated:

- Boot-safe driver sequence.
- MA730 velocity plausibility check.
- **APA102 global brightness pinned at 31** (lower values add ~580 Hz PWM, which shows as dashes in POV).
- SK9822 rejected for POV.
- Minimum-current parking for 24/7 clock mode.
- Stepper on 5 V with daily homing.

## 7. What was verified, and how

| Check | Result |
|---|---|
| `sch_netcheck.py` vs kicad-cli netlists (v0.5) | Exact match, both boards |
| v0.6 regenerated sheets, `--check` | 0 problems, both boards |
| v0.6 nets reviewed against intent | `review/*_v0.6_nets.txt` |
| All referenced footprints exist in KiCad 9.0.7 | Yes |
| CadQuery rebuild | Clean; only the hour hand is in front of the dial |
| **kicad-cli ERC on v0.6** | **Not run here** (KiCad couldn't be installed); KiBot CI runs it on push |
| Datasheet checks (XL4015 VC, SenRing G012 specs, LCSC ids) | **Not done**; marked *verify* |

## 8. Next steps (in order)

1. Let CI run kicad-cli ERC on the v0.6 sheets; fix anything it flags.
2. Confirm the XL4015 VC connection and the gimbal motor's bore against real parts.
3. Re-lay out both boards by hand (`docs/pcb-status.md`), then re-enable DRC (with no `ignore_unconnected`) and the fab outputs.
4. Prototype the coaxial shaft stack on the bench with the AS5600 fallback before committing to the MA730 satellite.
5. Write the firmware interlocks before the first spin test, with the guard fitted.
