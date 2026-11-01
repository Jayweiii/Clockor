# Firmware interlocks (hybrid v0.6)

Implement before any spin test. Status: **specified; firmware not yet written.**

## Boot / reset state (hardware-enforced in v0.6)

- DRV8313 `EN1–3` (GPIO6) and `nSLEEP`+`nRESET` (GPIO38) have **10 k pull-downs**, so the bridge stays off while the S3 boots, resets or is being flashed.
- Firmware sequence: drive `nSLEEP` high → wait ≥ 1 ms (charge pump) → read `nFAULT` (GPIO18) → enable `EN_ALL`.
- To clear a latched fault, pulse `nSLEEP`/`nRESET` low ≥ 1 µs with `EN_ALL` low.

## Minute BLDC (DRV8313 + SimpleFOC + MA730)

| Interlock | Behavior |
|-----------|----------|
| **Soft-start** | Ramp velocity over ≥ 500 ms. No step to target RPM. |
| **Encoder plausibility** | MA730 velocity must track the commanded velocity within ±15 % after the ramp. On a mismatch (stall, slip or loose magnet), spin down. |
| **Rotor index loss** | The C3 reports index presence in every heartbeat. If the DRV5023 index is missing for > 2 expected revolutions, the base spins down and blanks frames until re-sync. |
| **ESP-NOW heartbeat loss** | The base expects a rotor heartbeat every 200–500 ms. On loss: spin down, raise the fault LED; the C3 blanks the LEDs on its side when it loses base frames. |
| **LED current cap ~1.2 A** | Enforce in the C3 renderer before SPI out. Keep the APA102 **5-bit global brightness at 31** and scale the 8-bit colour values. Below 31 the APA102 adds a slow (~580 Hz) PWM that shows as dashes in POV. The SK9822 alternative has ~4.7 kHz PWM, slower than one display column (~140 µs at 1200 RPM / 360 columns), so avoid it for POV. |
| **Max RPM** | Software ceiling ≤ 1200 RPM (slip ring rated 5000; bar/hub not yet spin-tested). |
| **Supply** | Read `nFAULT`; refuse spin-up if VIN < 20 V (add an ADC divider in the next layout pass if needed). |
| **Mode exit** | Leaving graphics mode always soft-stops before parking as the minute hand. |
| **Parking** | Hold with the minimum FOC current that keeps position, since a balanced bar needs very little. Log temperature/current; a 24/7 hold is the main thermal load in clock mode. |

## Hour stepper (ULN2003A + 28BYJ-48, 5 V)

| Rule | Behavior |
|------|----------|
| **Supply** | Stepper common = **+5 V** (v0.5 wired it to the 12 V input, which would overheat a 5 V motor). |
| **Half-step** | 8-step table; ~4076 half-steps per output revolution → one step every ~10.6 s for 12 h/rev. |
| **De-energize between moves** | Release all ULN inputs after a ~50–100 ms settle. The gearbox holds the hand. |
| **Homing** | Step until `HR_HOME` asserts, then back off and re-approach slowly. Re-home daily. |

## Test hooks

- Fault inject: drop hall, kill ESP-NOW, command an over-bright frame, unplug the encoder → expect spin-down / clamp.
- Hour: scope the ULN inputs → pulses, then all-low between moves.
- Boot: hold the S3 in reset → confirm DRV8313 outputs are Hi-Z (pull-downs).
