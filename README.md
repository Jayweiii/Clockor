# clockor — POV clock hardware (hybrid v0.4)

Public KiCad 9 design package for a dual-mode clock: **spinning minute POV LED bar** + **slow physical hour hand** (off-axis stepper → hollow shaft). Jason / `Jayweiii`.

See **[docs/architecture.md](docs/architecture.md)**, **[docs/stack-up.md](docs/stack-up.md)**, **[docs/firmware-interlocks.md](docs/firmware-interlocks.md)**, and **[docs/changelog-review.md](docs/changelog-review.md)**.

## Locked mech (Chief Round 2)

| Item | P/N | Verified | Link |
|------|-----|----------|------|
| Minute BLDC | **Furitek KOMODO 2204 1400KV** | 12S14P (7 pole pairs) | https://furitek.com/products/furitek-2204-outrunner-1400kv-motor |
| Slip ring | **Mercotac 205** | 2×4 A, **2000 RPM** datasheet | https://www.mercotac.com/html/205.html |
| Dial | Clear acrylic / diffuser | ≥5 mm axial gap bar→dial incl. runout | `docs/stack-up.md` |

## Layout

```
hardware/
  base-controller/   ESP32-S3, XL4015, AMS1117, 1× DRV8313, ULN2003A, USB-C, slip + stepper headers
  hand-minute/       ESP32-C3-MINI-1, ME6211, 74AHCT125, 36× APA102-2020, AH1806, 470µF+TVS
  libs/              Clockor (DRV8313) + Espressif symbols/footprints
cad/                 Hybrid assembly (AS5600 rear, Mercotac front, off-axis hour)
docs/                Architecture, stack-up, firmware interlocks, LCSC, ERC waivers
bom/                 Per-board BOM CSVs
review/              ERC/DRC reports and export snapshots
scripts/             Schematic/PCB rebuild + place + experimental simple_route
.github/workflows/   KiBot ERC + manufacturing exports
```

## Tooling

- KiCad **9.0.7** (`kicad-cli sch erc`, `pcb drc`, exports)
- CI: [INTI-CMNB KiBot](https://github.com/INTI-CMNB/KiBot) via `.github/workflows/kibot.yml` (boards: `base-controller`, `hand-minute`)

## ERC status (authoritative: `review/*_erc.rpt`)

| Board | Errors | Warnings | Notes |
|-------|--------|----------|-------|
| base-controller | **0** | ~203 | See `docs/erc-waivers.md` |
| hand-minute | **0** | ~406 | |

## PCB / routing status

Footprints placed (`scripts/place_and_route.py`). **Not production-routed.** Freerouting native CLI crashes (GraalVM serialization). Experimental `scripts/simple_route.py` MST L-routes reduce unconnected but introduce shorts — **not committed as copper**. CI `run_drc: false` until a 0-error route exists.

## Rebuild

```bash
python3 scripts/rebuild_boards.py
python3 scripts/place_and_route.py
# optional experimental: python3 scripts/simple_route.py
```

## License

Public repository for Jason (`Jayweiii`). All rights reserved unless otherwise noted.
