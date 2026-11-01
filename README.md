# clockor — POV clock hardware (hybrid v0.6)

Public KiCad 9 design package for a dual-mode clock: a **spinning minute POV LED bar** plus a **slow physical hour hand** on a **coaxial hour shaft**. Jason / `Jayweiii`.

Start with **[docs/design-review-v0.6.md](docs/design-review-v0.6.md)**, then **[docs/architecture.md](docs/architecture.md)**, **[docs/stack-up.md](docs/stack-up.md)**, **[docs/firmware-interlocks.md](docs/firmware-interlocks.md)**, **[docs/pcb-status.md](docs/pcb-status.md)** and **[docs/changelog-review.md](docs/changelog-review.md)**.

## Status

| Area | State |
|---|---|
| Schematics | **v0.6**, regenerated; 0 problems from `scripts/sch_netcheck.py --check`. kicad-cli ERC runs in CI |
| PCBs | **v0.5 layouts, stale.** Need "Update PCB from Schematic" + hand routing. **Do not fabricate** |
| Mechanical CAD | v0.6 coaxial assembly (`cad/`, `renders/mech/`) |
| Firmware | Interlocks specified; code not written |

## Key parts (v0.6)

| Item | Part | Notes |
|------|------|-------|
| Minute BLDC | Hollow-shaft gimbal, 2804 class ~100 KV | 24 V bus; hour shaft passes through the bore |
| Minute encoder | MagAlpha MA730, side-shaft | SPI on `J10` |
| Hour | 28BYJ-48 5 V, coaxial at rear, 1:1 coupler | Only the hour hand is in front of the dial |
| Slip ring | SenRing G012 through-bore brush | 5 V + GND to the rotor |
| Rotor index | DRV5023 | Always-on hall |
| Dial | Clear acrylic | ≥ 5 mm axial gap bar → dial incl. runout |

## Layout

```
hardware/
  base-controller/   ESP32-S3, XL4015 (24→5 V), AMS1117, DRV8313, ULN2003A, USB-C sink + ESD, J9 hour home, J10 encoder
  hand-minute/       ESP32-C3-MINI-1, ME6211, 74AHCT125, 36× APA102-2020, DRV5023, 2×330 µF + TVS, J2 programming
  libs/              Clockor (DRV8313, DRV5023) + Espressif symbols/footprints
cad/                 Coaxial hybrid assembly (CadQuery)
docs/                Design review, architecture, stack-up, interlocks, sources, PCB status
bom/                 Per-board BOM CSVs generated from the schematics
review/              v0.6 net reports; v0.5 ERC/DRC reports and exports (historical)
scripts/             Generator, netlist checker, BOM export, experimental routers
.github/workflows/   KiBot ERC + schematic/BOM exports
```

## Rebuild

```bash
export KICAD9_SYMBOL_DIR=/usr/share/kicad/symbols        # KiCad 9 stock libraries
export KICAD9_FOOTPRINT_DIR=/usr/share/kicad/footprints
python3 scripts/rebuild_boards.py --sch-only             # schematics (+ connectivity check)
python3 scripts/sch_netcheck.py hardware/base-controller/base-controller.kicad_sch --check
python3 scripts/export_bom.py                            # bom/*.csv
python3 cad/build_assembly.py                            # needs cadquery
```

Without `--sch-only` the generator also recreates bare PCB shells for `scripts/place_and_route.py`. That discards the existing layouts.

## License

Public repository for Jason (`Jayweiii`). All rights reserved unless otherwise noted.
