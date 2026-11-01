# Open questions (hybrid v0.3)

1. **Exact BLDC** — which 2204/2205 KV and magnet pole count for SimpleFOC + AS5600 at 1200 RPM park/spin?
2. **Slip ring P/N** — 2-circuit, continuous current rating (target ≥2 A) and max RPM; wireless coil only if slip sourcing fails.
3. **Hour hand mounting** — confirm dial thickness / standoff so front stepper hand clears the spinning bar behind the dial.
4. **DRV8313 margin** — if 2204 stall/spin current exceeds comfort, move to DRV8316 + current sense (Chief #8).
5. **TPS54560** — only if XL4015 thermals fail at full LED + spin load.
6. **Guard / hub CAD** — clamp hub, balance procedure, and polycarbonate guard before first spin test.
7. **Freerouting / manual route** — boards still unrouted; enable DRC in CI after copper exists.
