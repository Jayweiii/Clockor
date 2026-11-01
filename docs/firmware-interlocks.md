# Firmware interlocks (hybrid v0.4 — Chief Round 2)

Implement before any spin test. Status: **documented / required**; firmware tree still scaffolding.

## Minute BLDC (DRV8313 + SimpleFOC + AS5600)

| Interlock | Behavior |
|-----------|----------|
| **Soft-start** | Ramp velocity / duty over ≥500 ms (configurable). No step to target RPM. |
| **Hall loss spin-down** | If AH1806 index missing for >2 expected revolutions (or timeout at commanded RPM), force ramp-down to stop and park attempt disabled until re-sync. |
| **ESP-NOW heartbeat loss** | Base S3 expects rotor C3 heartbeat (or ACK on frame window) within ~200–500 ms. On loss: command spin-down, blank or freeze last safe frame, raise fault LED on base. |
| **LED current cap ~1.2 A** | Global brightness / per-frame duty so Σ I_LED ≲ **1.2 A** at 5 V (well under Mercotac 4 A and slip thermal). Enforce in C3 renderer before SPI out. |
| **Max RPM** | Software ceiling ≤1200 RPM (Mercotac 205 rated 2000 RPM; leave margin). |
| **Mode exit** | Leaving graphics mode always soft-stops before parking as minute hand. |

## Hour stepper (ULN2003A + 28BYJ-48)

| Rule | Behavior |
|------|----------|
| **Half-step** | Drive sequence uses **half-step** tables (8-step), not full-step, for quieter motion and finer hour angle. |
| **De-energize between moves** | After each reposition (or settle delay ~50–100 ms), **release all ULN inputs** so coils are off. Holding torque from gearbox friction is enough for a light hand; reduces heat and idle current. |
| **No continuous hold current** | Do not leave two phases energized at idle. |

## Power / slip

- Rotor bulk ≥470 µF + SMAJ5.0A stay hardware.
- Firmware must not defeat the 1.2 A LED cap for “brighter” modes without a reviewed slip/thermal budget.

## Test hooks

- Fault inject: drop hall, kill ESP-NOW, command over-bright frame — expect spin-down / clamp.
- Hour: scope ULN inputs — pulses then all-low between moves.
