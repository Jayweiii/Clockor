# clockor — POV clock hardware

Private KiCad 9 design package for a dual-mode POV / analog-style clock: **base controller** plus **minute** and **hour** LED hands.

## Layout

```
hardware/
  base-controller/   ESP32-S3, XL4015, AMS1117, TCA9548A, 2× DRV8313, USB-C, slip/enc headers
  hand-minute/       ESP32-C3-MINI-1, ME6211, 74AHCT125, 36× APA102-2020
  hand-hour/         same architecture, 30× APA102-2020
  libs/              Clockor (DRV8313) + Espressif symbols/footprints
cad/                 Mechanical assembly (STEP/STL) from prior CAD pass
docs/                ERC waivers, notes
review/              ERC reports and export snapshots
scripts/             Schematic/PCB rebuild + place helpers
.github/workflows/   KiBot ERC/DRC + manufacturing exports
```

## Tooling

- KiCad **9.0.7** (`kicad-cli sch erc`, `pcb drc`, exports)
- CI: [INTI-CMNB KiBot](https://github.com/INTI-CMNB/KiBot) via `.github/workflows/kibot.yml`

## ERC status (authoritative: `review/*_erc.rpt`)

| Board | Errors | Warnings | Notes |
|-------|--------|----------|-------|
| base-controller | **0** | 237 | See `docs/erc-waivers.md` |
| hand-minute | **0** | 380 | |
| hand-hour | **0** | 332 | |

## PCB / routing status

Footprints are placed from the schematic netlist (`scripts/place_and_route.py`). **Autorouting is not complete** in the initial commit: the boxed `freerouting-cli` native build aborts mid-batch (GraalVM serialization on `ComponentOutline`). Boards are saved **placed, unrouted**; DRC will report unconnected items until routes/zones are finished. Follow-up commits may add SES import or manual routes.

## Rebuild (optional)

```bash
python3 scripts/rebuild_boards.py          # regenerate .kicad_sch / skeleton PCB helpers
# AppImage python3.10 + pcbnew:
python3.10 scripts/place_and_route.py      # netlist → place footprints → attempt Freerouting
```

## License / ownership

Private repository for Jason (`Jayweiii`). All rights reserved unless otherwise noted.
