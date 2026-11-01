# clockor — POV clock hardware (hybrid)

Public KiCad 9 design package for a dual-mode clock: **spinning minute POV LED bar** + **slow physical hour hand** (stepper). Jason / `Jayweiii`.

See **[docs/architecture.md](docs/architecture.md)** and **[docs/changelog-review.md](docs/changelog-review.md)**.

## Layout

```
hardware/
  base-controller/   ESP32-S3, XL4015, AMS1117, 1× DRV8313, ULN2003A, USB-C, slip + stepper headers
  hand-minute/       ESP32-C3-MINI-1, ME6211, 74AHCT125, 36× APA102-2020, AH1806, 470µF+TVS
  libs/              Clockor (DRV8313) + Espressif symbols/footprints
cad/                 Mechanical assembly from prior CAD pass
docs/                Architecture, review changelog, LCSC links, ERC waivers
bom/                 Per-board BOM CSVs
review/              ERC/DRC reports and export snapshots
scripts/             Schematic/PCB rebuild + place helpers
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

Footprints placed (rebuild + `scripts/place_and_route.py`). **Autorouting not complete** — Freerouting CLI still aborts; boards are **placed, unrouted**. CI runs ERC only (`run_drc: false`) until routes exist.

## Rebuild

```bash
python3 scripts/rebuild_boards.py
# AppImage python3.10 + pcbnew:
python3.10 scripts/place_and_route.py
```

## License

Public repository for Jason (`Jayweiii`). All rights reserved unless otherwise noted.
