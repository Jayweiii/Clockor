#!/usr/bin/env python3
"""Rebuild the Clockor KiCad schematics (and, without --sch-only, bare PCB shells).

Set KICAD9_SYMBOL_DIR / KICAD9_FOOTPRINT_DIR to the stock KiCad 9 library dirs
(defaults: /usr/share/kicad/{symbols,footprints}). Every run ends with
`sch_netcheck.check`, which fails on pin/label collisions, floating pins and
undriven power nets.
"""
from __future__ import annotations
import json, os, shutil, sys, uuid, re
from pathlib import Path
from datetime import datetime
sys.path.insert(0, str(Path(__file__).resolve().parent))
from symutil import resolve_symbol, pin_numbers, unit_count, lib_id as sym_lib_id

ROOT = Path(__file__).resolve().parents[1]
HW = ROOT / "hardware"
KICAD_FP = Path(os.environ.get("KICAD9_FOOTPRINT_DIR", "/usr/share/kicad/footprints"))
DATE = datetime.now().strftime("%Y-%m-%d")
SCH_VER = 20250114
PCB_VER = 20241229

def uid() -> str:
    return str(uuid.uuid4())

def write(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    print("wrote", path, "bytes", len(text))

# ---------- schematic primitives ----------
def begin_sheet(project: str = "clockor") -> str:
    """Allocate sheet UUID before emitting symbol instances."""
    global SHEET_UUID, PROJECT_NAME
    SHEET_UUID = uid()
    PROJECT_NAME = project
    return SHEET_UUID

def sch_header(title: str, paper="A3") -> str:
    global SHEET_UUID
    if not SHEET_UUID:
        SHEET_UUID = uid()
    return f'''(kicad_sch
\t(version {SCH_VER})
\t(generator "eeschema")
\t(generator_version "9.0")
\t(uuid "{SHEET_UUID}")
\t(paper "{paper}")
\t(title_block
\t\t(title "{title}")
\t\t(date "{DATE}")
\t\t(rev "0.2")
\t\t(company "Jason / clockor")
\t\t(comment 1 "Hybrid v0.6: spinning minute POV bar + coaxial stepper hour")
\t)
'''

def indent_block(block: str, tabs=1) -> str:
    pad = "\t" * tabs
    lines = block.strip("\n").split("\n")
    return "\n".join(pad + l if l else l for l in lines)

def lib_symbols_section(names: list[str]) -> str:
    parts = ["\t(lib_symbols"]
    seen = set()
    for n in names:
        if n in seen:
            continue
        seen.add(n)
        parts.append(indent_block(resolve_symbol(n), 2))
    parts.append("\t)")
    return "\n".join(parts)

def _qid(name: str) -> str:
    return name if ":" in name else sym_lib_id(name)

# Sheet UUID for symbol instances path — set by sch_header()
SHEET_UUID = ""
PROJECT_NAME = "clockor"

def instance(lib_id: str, ref: str, value: str, x: float, y: float, pins: list[str],
             footprint: str = "", unit: int = 1, extras: dict | None = None) -> str:
    lib_id = _qid(lib_id)
    pin_block = "\n".join(
        f'\t\t(pin "{p}"\n\t\t\t(uuid "{uid()}")\n\t\t)' for p in pins
    )
    extra_props = ""
    if extras:
        for k, v in extras.items():
            extra_props += f'''
\t\t(property "{k}" "{v}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)'''
    su = uid()
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} 0)
\t\t(unit {unit})
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{su}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x} {y - 7.62} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {x} {y + 7.62} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Footprint" "{footprint}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Description" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t){extra_props}
{pin_block}
\t\t(instances
\t\t\t(project "{PROJECT_NAME}"
\t\t\t\t(path "/{SHEET_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit {unit})
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''

def power_inst(lib_id: str, ref: str, x: float, y: float, rot: int = 0) -> str:
    lib_id = _qid(lib_id)
    value = lib_id.split(":", 1)[-1]
    su = uid()
    return f'''\t(symbol
\t\t(lib_id "{lib_id}")
\t\t(at {x} {y} {rot})
\t\t(unit 1)
\t\t(exclude_from_sim no)
\t\t(in_bom no)
\t\t(on_board yes)
\t\t(dnp no)
\t\t(uuid "{su}")
\t\t(property "Reference" "{ref}"
\t\t\t(at {x} {y + 2.54} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Value" "{value}"
\t\t\t(at {x} {y - 2.54} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t)
\t\t)
\t\t(property "Footprint" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Datasheet" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(property "Description" ""
\t\t\t(at {x} {y} 0)
\t\t\t(effects
\t\t\t\t(font
\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t)
\t\t\t\t(hide yes)
\t\t\t)
\t\t)
\t\t(pin "1"
\t\t\t(uuid "{uid()}")
\t\t)
\t\t(instances
\t\t\t(project "{PROJECT_NAME}"
\t\t\t\t(path "/{SHEET_UUID}"
\t\t\t\t\t(reference "{ref}")
\t\t\t\t\t(unit 1)
\t\t\t\t)
\t\t\t)
\t\t)
\t)
'''

def label(name: str, x: float, y: float, rot: int = 0) -> str:
    return f'''\t(label "{name}"
\t\t(at {x} {y} {rot})
\t\t(fields_autoplaced yes)
\t\t(effects (font (size 1.27 1.27)) (justify left bottom))
\t\t(uuid "{uid()}")
\t)
'''

def glabel(name: str, x: float, y: float, shape="input", rot: int = 0) -> str:
    return f'''\t(global_label "{name}"
\t\t(shape {shape})
\t\t(at {x} {y} {rot})
\t\t(fields_autoplaced yes)
\t\t(effects (font (size 1.27 1.27)) (justify left))
\t\t(uuid "{uid()}")
\t\t(property "Intersheetrefs" "${{INTERSHEET_REFS}}"
\t\t\t(at {x} {y} 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t)
'''

def wire(x1, y1, x2, y2) -> str:
    return f'''\t(wire
\t\t(pts (xy {x1} {y1}) (xy {x2} {y2}))
\t\t(stroke (width 0) (type default))
\t\t(uuid "{uid()}")
\t)
'''

def noconnect(x, y) -> str:
    return f'''\t(no_connect (at {x} {y}) (uuid "{uid()}"))
'''

def text(x, y, s, size=1.5) -> str:
    return f'''\t(text "{s}"
\t\t(exclude_from_sim no)
\t\t(at {x} {y} 0)
\t\t(effects (font (size {size} {size})) (justify left bottom))
\t\t(uuid "{uid()}")
\t)
'''

def junction(x, y) -> str:
    return f'''\t(junction (at {x} {y}) (diameter 0) (color 0 0 0 0) (uuid "{uid()}"))
'''

def sch_footer() -> str:
    return '''\t(sheet_instances
\t\t(path "/"
\t\t\t(page "1")
\t\t)
\t)
\t(embedded_fonts no)
)
'''

# Pin coordinate helpers — approximate from symbol geometry for wiring labels near chips
# For ERC, labels only need to touch a wire that touches a pin. We'll place labels at
# documented offsets next to symbols and connect with short wires to known pin positions.
# Simpler ERC strategy: use hierarchical/global labels ON the pin positions from resolved symbols.

def _snap(v: float, grid: float = 1.27) -> float:
    return round(float(v) / grid) * grid

def pin_positions(resolved: str, name: str, origin: tuple[float, float], unit: int = 1) -> dict[str, tuple[float, float, int]]:
    """Return {pin_num: (abs_x, abs_y, rotation)} for unit."""
    # Find unit block name_unit_1 (pins live in *_1_* drawing units typically)
    # Collect all pins from symbol regardless of subunit
    pos = {}
    for m in re.finditer(
        r'\(pin \w+ \w+\s+\(at ([-\d.]+) ([-\d.]+) (\d+)\)\s+\(length ([-\d.]+)\).*?\(number "([^"]+)"',
        resolved,
        re.S,
    ):
        px, py, rot, length, num = float(m.group(1)), float(m.group(2)), int(m.group(3)), float(m.group(4)), m.group(5)
        # absolute = origin + local (KiCad sch: symbol at origin, pins relative)
        pos[num] = (origin[0] + px, origin[1] - py, rot)  # symbol +Y up; schematic +Y down
    return pos


def drive_net(parts: list, pwr_counter: list, net: str, x: float, y: float, with_flag: bool = True):
    """Place power symbol (and optional PWR_FLAG) on net at (x,y) with short wires."""
    i = pwr_counter[0]
    pwr_counter[0] += 1
    ref = f"#PWR{i:02d}"
    # Power symbol pin is at its origin
    parts.append(power_inst(net if net not in ("VIN_24V", "VBUS") else "PWR_FLAG", ref, x, y))
    if net in ("VIN_24V", "VBUS"):
        # PWR_FLAG only — label provides the name; flag drives the net for ERC
        parts.append(label(net, x, y + 2.54))
        parts.append(wire(x, y, x, y + 2.54))
        return
    parts.append(label(net, x, y + 2.54))
    parts.append(wire(x, y, x, y + 2.54))
    if with_flag:
        i = pwr_counter[0]
        pwr_counter[0] += 1
        ref2 = f"#FLG{i:02d}"
        parts.append(power_inst("PWR_FLAG", ref2, x + 5.08, y))
        parts.append(wire(x, y, x + 5.08, y))


def connect_label_to_pin(pname: str, pin_xyz: tuple[float, float, int], stub: float = 2.54) -> str:
    """Wire stub from exact pin tip outward; label at far end."""
    x, y, rot = pin_xyz
    # rot = direction pin points (body -> tip). Continue outward past tip.
    if rot == 0:
        dx, dy = stub, 0.0
    elif rot == 180:
        dx, dy = -stub, 0.0
    elif rot == 90:
        dx, dy = 0.0, -stub
    elif rot == 270:
        dx, dy = 0.0, stub
    else:
        dx, dy = stub, 0.0
    x2, y2 = x + dx, y + dy
    out = []
    out.append(wire(x, y, x2, y2))
    lab_rot = 0 if rot in (90, 270) else rot
    out.append(label(pname, x2, y2, lab_rot))
    return "".join(out)


KEEP_EXISTING_PRO = False  # --sch-only: never clobber board rules / net classes


def write_pro(path: Path, name: str):
    if KEEP_EXISTING_PRO and path.exists():
        print('kept', path)
        return
    data = {
        "board": {
            "design_settings": {
                "defaults": {"board_outline_line_width": 0.1, "copper_line_width": 0.2},
                "rules": {"min_clearance": 0.2, "min_track_width": 0.2, "min_via_diameter": 0.6, "min_via_drill": 0.3},
            }
        },
        "meta": {"filename": f"{name}.kicad_pro", "version": 3},
        "project": {"files": []},
        "schematic": {
            "drawing": {
                "default_line_thickness": 6.0,
                "default_text_size": 50.0,
                "pin_symbol_size": 0.0,
            },
            "connectivity": {},
            "erc": {
                "erc_exclusions": [],
                "meta": {"version": 0},
                "pin_map": [[0,0,0,0,0,0,1,0,0,0,0,2],
                            [0,2,0,1,0,0,1,0,2,2,2,2],
                            [0,0,0,0,0,0,1,0,1,0,1,2],
                            [0,1,0,0,0,0,1,1,2,1,1,2],
                            [0,0,0,0,0,0,1,0,0,0,0,2],
                            [0,0,0,0,0,0,0,0,0,0,0,2],
                            [1,1,1,1,1,0,1,1,1,1,1,2],
                            [0,0,0,1,0,0,1,0,0,0,0,2],
                            [0,2,1,2,0,0,1,0,2,2,2,2],
                            [0,2,0,1,0,0,1,0,2,0,0,2],
                            [0,2,1,1,0,0,1,0,2,0,0,2],
                            [2,2,2,2,2,2,2,2,2,2,2,2]],
                "rule_severities": {
                    "endpoint_off_grid": "warning",
                    "lib_symbol_issues": "warning",
                    "footprint_link_issues": "warning",
                    "unconnected_wire_endpoint": "warning",
                    "no_connect_dangling": "warning",
                    "multiple_net_names": "warning",
                    "label_dangling": "error",
                    "pin_not_connected": "error",
                    "pin_not_driven": "error",
                    "power_pin_not_driven": "error",
                    "pin_to_pin": "error",
                },
            },
        },
        "sheets": [[f"{name}.kicad_sch", "Root"]],
        "text_variables": {},
    }
    write(path, json.dumps(data, indent=2))

def write_fp_lib_table(path: Path, extras: list[tuple[str, str]]):
    rows = ['(fp_lib_table', '  (version 7)']
    # Prefer local then KiCad stock via env — for project, list local + nicknames pointing to stock paths
    for nick, uri in extras:
        rows.append(f'  (lib (name "{nick}")(type "KiCad")(uri "{uri}")(options "")(descr ""))')
    rows.append(')')
    write(path, "\n".join(rows) + "\n")

def write_sym_lib_table(path: Path, extras: list[tuple[str, str]]):
    rows = ['(sym_lib_table', '  (version 7)']
    for nick, uri in extras:
        rows.append(f'  (lib (name "{nick}")(type "KiCad")(uri "{uri}")(options "")(descr ""))')
    rows.append(')')
    write(path, "\n".join(rows) + "\n")

# =========================================================================
# BASE CONTROLLER SCHEMATIC — HYBRID v0.5
# Minute: 1× DRV8313 + AS5600 on I2C0. Hour: ULN2003A + 28BYJ-48 off-axis 1:1 dial stub + AH1806 home.
# No TCA9548A. No second BLDC. No hour rotor board.
# =========================================================================
def build_base_sch(outdir: Path):
    name = "base-controller"
    begin_sheet(name)
    FP = {
        "ESP32-S3-WROOM-1": "RF_Module:ESP32-S3-WROOM-1",
        "XL4015": "Package_TO_SOT_SMD:TO-263-5_TabPin3",
        "AMS1117-3.3": "Package_TO_SOT_SMD:SOT-223-3_TabPin2",
        "DRV8313": "Package_SO:HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.5mm_ThermalVias",
        "ULN2003A": "Package_SO:SOIC-16_3.9x9.9mm_P1.27mm",
        "USB": "Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12",
        "Barrel": "Connector_BarrelJack:BarrelJack_CUI_PJ-036AH-SMT_Horizontal",  # pinned (v0.5 used first glob hit)
        "R": "Resistor_SMD:R_0603_1608Metric",
        "C": "Capacitor_SMD:C_0603_1608Metric",
        "C0805": "Capacitor_SMD:C_0805_2012Metric",
        "CP": "Capacitor_SMD:CP_Elec_10x10",
        "D": "Diode_SMD:D_SMA",
        "L": "Inductor_SMD:L_TaiTech_TMPC1265_13.5x12.5mm",
        "LED": "LED_SMD:LED_0603_1608Metric",
        "SW": "Button_Switch_SMD:SW_SPST_CK_RS282G05A3",
        "HDR4": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "HDR5": "Connector_PinHeader_2.54mm:PinHeader_1x05_P2.54mm_Vertical",
        "HDR6": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
        "HDR3": "Connector_PinHeader_2.54mm:PinHeader_1x03_P2.54mm_Vertical",
        "C1206": "Capacitor_SMD:C_1206_3216Metric",
        "SOT23-6": "Package_TO_SOT_SMD:SOT-23-6",
    }
    syms = [
        "ESP32-S3-WROOM-1", "XL4015", "AMS1117-3.3", "DRV8313", "ULN2003A",
        "USB_C_Receptacle_USB2.0_16P", "Barrel_Jack", "Conn_01x04", "Conn_01x05", "Conn_01x03",
        "Conn_01x06", "USBLC6-2SC6", "D_Schottky",
        "R", "C", "C_Polarized", "D", "L", "LED", "SW_Push",
        "GND", "+3V3", "+5V", "PWR_FLAG",
    ]

    parts = []
    pwr_i = 1

    def two_pin(sym, ref, value, xy, fp, net_a, net_b):
        b = resolve_symbol(sym)
        parts.append(instance(sym, ref, value, xy[0], xy[1], pin_numbers(b), fp))
        pos = pin_positions(b, sym, xy)
        if "1" in pos:
            parts.append(connect_label_to_pin(net_a, pos["1"]))
        if "2" in pos:
            parts.append(connect_label_to_pin(net_b, pos["2"]))

    # --- U1 ESP32-S3 ---
    u1 = (50.8, 63.5)
    esp_block = resolve_symbol("ESP32-S3-WROOM-1")
    parts.append(instance("ESP32-S3-WROOM-1", "U1", "ESP32-S3-WROOM-1-N16R8", u1[0], u1[1], pin_numbers(esp_block), FP["ESP32-S3-WROOM-1"]))
    esp_pos = pin_positions(esp_block, "ESP32-S3-WROOM-1", u1)

    for pn, net in [("2", "+3V3"), ("1", "GND"), ("40", "GND"), ("41", "GND")]:
        if pn in esp_pos:
            parts.append(connect_label_to_pin(net, esp_pos[pn]))
    if "3" in esp_pos:
        parts.append(connect_label_to_pin("EN_ESP", esp_pos["3"]))
    for pn, net in [("13", "USB_D-"), ("14", "USB_D+")]:
        if pn in esp_pos:
            parts.append(connect_label_to_pin(net, esp_pos[pn]))
    if "27" in esp_pos:
        parts.append(connect_label_to_pin("BOOT", esp_pos["27"]))

    # I2C0 → AS5600 minute encoder (no mux). I2C1 reserved / header.
    # Espressif WROOM-1: pin12=GPIO8 SDA-ish, pin17=GPIO9 SCL (same as prior)
    for pn, net in [("12", "I2C0_SDA"), ("17", "I2C0_SCL")]:
        if pn in esp_pos:
            parts.append(connect_label_to_pin(net, esp_pos[pn]))
    # Second I2C bus on GPIO1/GPIO2 (pins 39/38) — breakout only
    for pn, net in [("39", "I2C1_SDA"), ("38", "I2C1_SCL")]:
        if pn in esp_pos:
            parts.append(connect_label_to_pin(net, esp_pos[pn]))

    # WROOM-1 pad → GPIO (v0.6). Strapping pins GPIO0/3/45/46 carry nothing that
    # pulls them the wrong way at reset; GPIO35-37 are reserved for octal PSRAM (N16R8).
    #   pad 15 GPIO3  M1_IN1   | pad 4 GPIO4 M1_IN2 | pad 5 GPIO5 M1_IN3
    #   pad 6  GPIO6  M1_EN_ALL (EN1-3, 10k pull-down → bridges off at boot)
    #   pad 31 GPIO38 M1_nSLEEP (nSLEEP+nRESET, 10k pull-down → driver asleep at boot)
    #   pad 11 GPIO18 M1_nFAULT (was GPIO46: pull-up on a strap pin blocked download mode)
    #   pads 7-10 GPIO7/15/16/17 HR_IN1-4 | pad 19 GPIO11 HR_HOME
    #   pads 20/21/22/32 GPIO12/13/14/39 encoder SPI (SCK/MISO/MOSI/CS)
    gpio_map = [
        ("15", "M1_IN1"), ("4", "M1_IN2"), ("5", "M1_IN3"), ("6", "M1_EN_ALL"),
        ("31", "M1_nSLEEP"), ("11", "M1_nFAULT"),
        ("7", "HR_IN1"), ("8", "HR_IN2"), ("9", "HR_IN3"), ("10", "HR_IN4"),
        ("23", "MODE_BTN"), ("18", "STATUS_LED"),
        ("19", "HR_HOME"),
        ("20", "ENC_SCK"), ("21", "ENC_MISO"), ("22", "ENC_MOSI"), ("32", "ENC_CS"),
    ]
    used_esp = {"1", "2", "3", "13", "14", "27", "12", "17", "40", "41", "39", "38"}
    for pn, net in gpio_map:
        if pn in esp_pos:
            parts.append(connect_label_to_pin(net, esp_pos[pn]))
            used_esp.add(pn)
    for pn, xyz in esp_pos.items():
        if pn not in used_esp:
            parts.append(noconnect(xyz[0], xyz[1]))

    # --- U2 XL4015 ---
    u2 = (30.48, 114.3)
    xl = resolve_symbol("XL4015")
    parts.append(instance("XL4015", "U2", "XL4015E1", u2[0], u2[1], pin_numbers(xl), FP["XL4015"]))
    xl_pos = pin_positions(xl, "XL4015", u2)
    # VC = internal regulator bypass: 1 µF from VC to VIN (C27) per XL4015 typical
    # application. v0.5 tied VC straight to the 5 V output.
    for pn, net in [("5", "VIN_24V"), ("1", "GND"), ("3", "BUCK_SW"), ("2", "BUCK_FB"), ("4", "BUCK_VC")]:
        if pn in xl_pos:
            parts.append(connect_label_to_pin(net, xl_pos[pn]))

    # --- U3 AMS1117-3.3 ---
    u3 = (70.0, 114.3)
    ams = resolve_symbol("AMS1117-3.3")
    parts.append(instance("AMS1117-3.3", "U3", "AMS1117-3.3", u3[0], u3[1], pin_numbers(ams), FP["AMS1117-3.3"]))
    ams_pos = pin_positions(ams, "AMS1117-3.3", u3)
    for pn, net in [("1", "GND"), ("2", "+3V3"), ("3", "+5V")]:
        if pn in ams_pos:
            parts.append(connect_label_to_pin(net, ams_pos[pn]))

    # --- U5 DRV8313 (minute BLDC only) ---
    def place_drv(ref, origin, prefix):
        drv = resolve_symbol("DRV8313")
        parts.append(instance("DRV8313", ref, "DRV8313PWPR", origin[0], origin[1], pin_numbers(drv), FP["DRV8313"]))
        pos = pin_positions(drv, "DRV8313", origin)
        mapping = {
            "27": f"{prefix}_IN1", "25": f"{prefix}_IN2", "23": f"{prefix}_IN3",
            "26": f"{prefix}_EN1", "24": f"{prefix}_EN2", "22": f"{prefix}_EN3",
            "17": f"{prefix}_nSLEEP", "16": f"{prefix}_nRESET",
            "5": f"{prefix}_OUTA", "8": f"{prefix}_OUTB", "9": f"{prefix}_OUTC",
            "18": f"{prefix}_nFAULT",
            "4": "VIN_24V", "11": "VIN_24V",
            "14": "GND", "20": "GND", "28": "GND",
            "6": "GND", "7": "GND", "10": "GND",
            "15": f"{prefix}_V3P3",
            "1": f"{prefix}_CPL", "2": f"{prefix}_CPH", "3": f"{prefix}_VCP",
        }
        used = set()
        for pn, net in mapping.items():
            if pn in pos:
                parts.append(connect_label_to_pin(net, pos[pn]))
                used.add(pn)
        for pn, xyz in pos.items():
            if pn not in used:
                parts.append(noconnect(xyz[0], xyz[1]))

    place_drv("U5", (200.0, 50.8), "M1")

    # --- U4 ULN2003A hour stepper ---
    u4 = (200.0, 120.0)
    uln = resolve_symbol("ULN2003A")
    parts.append(instance("ULN2003A", "U4", "ULN2003ADR", u4[0], u4[1], pin_numbers(uln), FP["ULN2003A"]))
    uln_pos = pin_positions(uln, "ULN2003A", u4)
    uln_map = {
        "1": "HR_IN1", "2": "HR_IN2", "3": "HR_IN3", "4": "HR_IN4",
        "5": "GND", "6": "GND", "7": "GND",  # unused inputs tied low
        "8": "GND",
        "9": "+5V",  # COM flyback clamp = stepper supply (5 V 28BYJ-48; v0.5 put 12 V here)
        "16": "HR_OUT1", "15": "HR_OUT2", "14": "HR_OUT3", "13": "HR_OUT4",
    }
    used = set(uln_map)
    for pn, net in uln_map.items():
        if pn in uln_pos:
            parts.append(connect_label_to_pin(net, uln_pos[pn]))
    for pn, xyz in uln_pos.items():
        if pn not in used:
            parts.append(noconnect(xyz[0], xyz[1]))

    # USB-C (UFP / sink). v0.5 bugs fixed: VBUS pins were on GND, CC1 collided with
    # the +5V PWR_FLAG wire, no Rd. Now: VBUS net, 5.1k Rd on each CC, ESD on D±,
    # VBUS → Schottky → +5V so logic can be flashed from USB alone (motors need VIN).
    j2 = (20.32, 63.5)
    usb = resolve_symbol("USB_C_Receptacle_USB2.0_16P")
    parts.append(instance("USB_C_Receptacle_USB2.0_16P", "J2", "TYPE-C-31-M-12", j2[0], j2[1], pin_numbers(usb), FP["USB"]))
    usb_pos = pin_positions(usb, "USB_C_Receptacle_USB2.0_16P", j2)
    usb_map = {
        "A6": "USB_D+", "B6": "USB_D+", "A7": "USB_D-", "B7": "USB_D-",
        "A4": "VBUS", "A9": "VBUS", "B4": "VBUS", "B9": "VBUS",
        "A5": "USB_CC1", "B5": "USB_CC2",
        "A1": "GND", "A12": "GND", "B1": "GND", "B12": "GND", "S1": "GND",
    }
    used = set(usb_map)
    for pn, net in usb_map.items():
        if pn in usb_pos:
            parts.append(connect_label_to_pin(net, usb_pos[pn]))
    for pn, xyz in usb_pos.items():
        if pn not in used:
            parts.append(noconnect(xyz[0], xyz[1]))

    # Barrel jack
    j1 = (20.32, 114.3)
    bj = resolve_symbol("Barrel_Jack")
    parts.append(instance("Barrel_Jack", "J1", "DC005-2.5", j1[0], j1[1], pin_numbers(bj), FP["Barrel"]))
    bj_pos = pin_positions(bj, "Barrel_Jack", j1)
    if "1" in bj_pos:
        parts.append(connect_label_to_pin("VIN_24V", bj_pos["1"]))
    if "2" in bj_pos:
        parts.append(connect_label_to_pin("GND", bj_pos["2"]))

    def hdr(ref, xy, nets, sym="Conn_01x04", fpkey="HDR4"):
        c = resolve_symbol(sym)
        parts.append(instance(sym, ref, sym, xy[0], xy[1], pin_numbers(c), FP[fpkey]))
        pos = pin_positions(c, sym, xy)
        for i, net in enumerate(nets, 1):
            if str(i) in pos:
                parts.append(connect_label_to_pin(net, pos[str(i)]))

    # BLDC phase out
    hdr("J3", (270.0, 40.64), ["M1_OUTA", "M1_OUTB", "M1_OUTC", "GND"])
    # I2C0 header (AS5600 bench fallback / accessories). The v0.6 coaxial shaft has
    # no free rear shaft end, so the primary minute encoder is SPI (J10).
    hdr("J5", (140.0, 30.48), ["+3V3", "GND", "I2C0_SDA", "I2C0_SCL"])
    # I2C1 breakout (unused / future)
    hdr("J6", (140.0, 50.8), ["+3V3", "GND", "I2C1_SDA", "I2C1_SCL"])
    # Minute encoder satellite: MagAlpha MA730 side-shaft + ring magnet on hollow minute shaft
    hdr("J10", (140.0, 71.12), ["+3V3", "GND", "ENC_SCK", "ENC_MISO", "ENC_MOSI", "ENC_CS"], "Conn_01x06", "HDR6")
    # Single slip ring → spinning minute bar (5V + GND only)
    hdr("J7", (100.0, 140.0), ["SLIP_5V", "SLIP_GND", "GND", "+5V"])
    # Hour stepper 5-pin: common (+5 V, 5 V 28BYJ-48) + 4 coils
    hdr("J8", (160.0, 140.0), ["+5V", "HR_OUT1", "HR_OUT2", "HR_OUT3", "HR_OUT4"], "Conn_01x05", "HDR5")

    # Hour home: remote hall on the rear hour-shaft coupler (magnet on coupler) via J9.
    # v0.5 also had U6 on this PCB — it could never see the magnet and sat in
    # parallel with J9, so it is removed. R22 pull-up for an open-drain sensor.
    two_pin("R", "R22", "10k", (200.0, 160.0), FP["R"], "HR_HOME", "+3V3")
    hdr("J9", (220.0, 160.0), ["+3V3", "GND", "HR_HOME"], "Conn_01x03", "HDR3")
    two_pin("C", "C26", "100nF", (235.0, 160.0), FP["C"], "HR_HOME", "GND")  # cable noise filter

    # USB-C support: Rd on CC, ESD array, VBUS OR-ing diode
    two_pin("R", "R23", "5.1k", (20.0, 95.0), FP["R"], "USB_CC1", "GND")
    two_pin("R", "R24", "5.1k", (30.0, 95.0), FP["R"], "USB_CC2", "GND")
    two_pin("D_Schottky", "D3", "SS34", (100.0, 180.0), FP["D"], "+5V", "VBUS")  # pin1 = K
    esd = resolve_symbol("USBLC6-2SC6")
    u7 = (100.0, 200.0)
    parts.append(instance("USBLC6-2SC6", "U7", "USBLC6-2SC6", u7[0], u7[1], pin_numbers(esd), FP["SOT23-6"]))
    ep = pin_positions(esd, "USBLC6-2SC6", u7)
    for pn, net in [("1", "USB_D+"), ("6", "USB_D+"), ("3", "USB_D-"), ("4", "USB_D-"), ("5", "VBUS"), ("2", "GND")]:
        if pn in ep:
            parts.append(connect_label_to_pin(net, ep[pn]))

    # Slip aliases
    parts.append(wire(90, 150, 110, 150))
    parts.append(label("+5V", 90, 150))
    parts.append(label("SLIP_5V", 110, 150))
    parts.append(wire(90, 155, 110, 155))
    parts.append(label("GND", 90, 155))
    parts.append(label("SLIP_GND", 110, 155))

    # Passives
    two_pin("L", "L1", "47uH", (45.0, 130.0), FP["L"], "BUCK_SW", "+5V")
    two_pin("D", "D1", "SS54", (55.0, 130.0), FP["D"], "BUCK_SW", "GND")
    two_pin("C_Polarized", "C1", "470uF 35V", (25.0, 130.0), FP["CP"], "VIN_24V", "GND")
    two_pin("C", "C27", "1uF 50V", (35.0, 150.0), FP["C0805"], "BUCK_VC", "VIN_24V")
    two_pin("C_Polarized", "C2", "470uF", (65.0, 130.0), FP["CP"], "+5V", "GND")
    two_pin("C", "C3", "22uF", (85.0, 130.0), FP["C0805"], "+3V3", "GND")
    two_pin("C", "C4", "10uF", (95.0, 130.0), FP["C0805"], "+5V", "GND")
    for i, ref in enumerate(["C10", "C11", "C12", "C13", "C14", "C15"]):
        two_pin("C", ref, "100nF", (110.0 + i * 10, 160.0), FP["C"], "+3V3", "GND")

    two_pin("R", "R1", "1k", (50.0, 90.0), FP["R"], "STATUS_LED", "LED_K")
    two_pin("LED", "D2", "LED_R", (60.0, 90.0), FP["LED"], "LED_K", "GND")
    two_pin("R", "R2", "4.7k", (120.0, 90.0), FP["R"], "I2C0_SDA", "+3V3")
    two_pin("R", "R3", "4.7k", (130.0, 90.0), FP["R"], "I2C0_SCL", "+3V3")
    two_pin("R", "R4", "1k", (40.0, 140.0), FP["R"], "BUCK_FB", "GND")
    two_pin("R", "R5", "3.00k", (50.0, 140.0), FP["R"], "BUCK_FB", "+5V")
    two_pin("R", "R20", "10k", (40.0, 90.0), FP["R"], "EN_ESP", "+3V3")
    two_pin("R", "R21", "10k", (250.0, 30.0), FP["R"], "M1_nFAULT", "+3V3")
    two_pin("R", "R6", "4.7k", (150.0, 90.0), FP["R"], "I2C1_SDA", "+3V3")
    two_pin("R", "R7", "4.7k", (160.0, 90.0), FP["R"], "I2C1_SCL", "+3V3")

    # Buttons spaced ≥ 20 mm: v0.5 put SW1 pin 2 and SW2 pin 1 0.16 mm apart.
    two_pin("SW_Push", "SW1", "BOOT", (70.0, 90.0), FP["SW"], "BOOT", "GND")
    two_pin("SW_Push", "SW2", "MODE", (90.0, 90.0), FP["SW"], "MODE_BTN", "GND")

    # DRV8313 control: EN1-3 together (GPIO6), nSLEEP+nRESET together (GPIO38).
    # Both pulled low so the bridge is off/asleep while the S3 boots or resets.
    x0, stub_y = 200, 170
    for nets in (["M1_EN_ALL", "M1_EN1", "M1_EN2", "M1_EN3"], ["M1_nSLEEP", "M1_nRESET"]):
        for i, n in enumerate(nets):
            parts.append(label(n, x0 + i * 15, stub_y))
            if i:
                parts.append(wire(x0 + (i - 1) * 15, stub_y, x0 + i * 15, stub_y))
        stub_y += 10
    two_pin("R", "R25", "10k", (270.0, 200.0), FP["R"], "M1_EN_ALL", "GND")
    two_pin("R", "R26", "10k", (285.0, 200.0), FP["R"], "M1_nSLEEP", "GND")

    # Charge-pump caps (KiBot-safe refs)
    two_pin("C", "C20", "10nF", (250, 170), FP["C"], "M1_CPH", "M1_CPL")
    two_pin("C", "C21", "100nF", (250, 180), FP["C"], "M1_VCP", "VIN_24V")
    two_pin("C", "C22", "470nF", (250, 190), FP["C"], "M1_V3P3", "GND")
    # VM local decoupling at DRV8313 pins 4 and 11 (v0.5 relied on C1 only)
    two_pin("C", "C23", "100nF 50V", (250, 210), FP["C"], "VIN_24V", "GND")
    two_pin("C", "C24", "100nF 50V", (260, 210), FP["C"], "VIN_24V", "GND")
    two_pin("C", "C25", "10uF 50V", (270, 220), FP["C1206"], "VIN_24V", "GND")

    # Power
    pwr_counter = [pwr_i]
    drive_net(parts, pwr_counter, "+3V3", 15.24, 20.32, with_flag=False)
    drive_net(parts, pwr_counter, "+5V", 30.48, 20.32, with_flag=True)  # KiBot wants flag
    drive_net(parts, pwr_counter, "GND", 45.72, 20.32, with_flag=True)
    drive_net(parts, pwr_counter, "VIN_24V", 15.24, 114.3)
    drive_net(parts, pwr_counter, "VBUS", 60.0, 20.32)

    parts.append(text(10, 10, "POV Clock — Base Controller HYBRID v0.6", 2.0))
    parts.append(text(10, 15, "ESP32-S3 + DRV8313 (24 V gimbal BLDC) + ULN2003A (5 V 28BYJ-48, coaxial hour shaft)", 1.2))
    parts.append(text(10, 18, "USB-C sink + ESD; encoder SPI J10 (MA730 side-shaft); hour home remote via J9.", 1.0))

    body = sch_header("POV Clock — Base Controller (Hybrid)")
    # bump rev in header via replace
    body = body.replace('(rev "0.2")', '(rev "0.6")')
    body += lib_symbols_section(syms) + "\n"
    body += "".join(parts)
    body += sch_footer()
    write(outdir / f"{name}.kicad_sch", body)
    write_pro(outdir / f"{name}.kicad_pro", name)
    return name


# =========================================================================
# SPINNING MINUTE / POV BAR SCHEMATIC — HYBRID v0.3
# Counterbalanced diametric bar; hall index; 470uF + TVS; ME6211 kept.
# =========================================================================
def build_hand_sch(outdir: Path, which: str, length_mm: int, led_count: int):
    name = f"hand-{which}"
    begin_sheet(name)
    FP = {
        "ESP32-C3-MINI-1": "Espressif:ESP32-C3-MINI-1",
        "ME6211C33M5": "Package_TO_SOT_SMD:SOT-23-5",
        "74AHCT125": "Package_SO:TSSOP-14_4.4x5mm_P0.65mm",
        "APA102-2020": "LED_SMD:LED-APA102-2020",
        "DRV5023": "Package_TO_SOT_SMD:SOT-23",
        "SMAJ5.0A": "Diode_SMD:D_SMA",
        "CPOLY": "Capacitor_Tantalum_SMD:CP_EIA-7343-31_Kemet-D",
        "HDR6": "Connector_PinHeader_2.54mm:PinHeader_1x06_P2.54mm_Vertical",
        "R": "Resistor_SMD:R_0603_1608Metric",
        "C": "Capacitor_SMD:C_0603_1608Metric",
        "C0805": "Capacitor_SMD:C_0805_2012Metric",
        "CP": "Capacitor_SMD:CP_Elec_10x10",
        "SW": "Button_Switch_SMD:SW_SPST_CK_RS282G05A3",
        "HDR4": "Connector_PinHeader_2.54mm:PinHeader_1x04_P2.54mm_Vertical",
        "TP": "TestPoint:TestPoint_Pad_D2.5mm",
    }
    syms = [
        "ESP32-C3-MINI-1", "ME6211C33M5", "74AHCT125", "APA102-2020",
        "DRV5023", "SMAJ5.0A", "TestPoint",
        "R", "C", "C_Polarized", "Conn_01x04", "Conn_01x06", "SW_Push",
        "GND", "+3V3", "+5V", "PWR_FLAG",
    ]
    parts = []
    pwr_i = 1

    def two_pin(sym, ref, value, xy, fp, net_a, net_b):
        b = resolve_symbol(sym)
        parts.append(instance(sym, ref, value, xy[0], xy[1], pin_numbers(b), fp))
        pos = pin_positions(b, sym, xy)
        if "1" in pos:
            parts.append(connect_label_to_pin(net_a, pos["1"]))
        if "2" in pos:
            parts.append(connect_label_to_pin(net_b, pos["2"]))

    # U1 ESP32-C3-MINI-1
    u1 = (50.8, 50.8)
    c3 = resolve_symbol("ESP32-C3-MINI-1")
    parts.append(instance("ESP32-C3-MINI-1", "U1", "ESP32-C3-MINI-1-N4", u1[0], u1[1], pin_numbers(c3), FP["ESP32-C3-MINI-1"]))
    pos = pin_positions(c3, "ESP32-C3-MINI-1", u1)
    used = set()
    for pn, net in [
        ("3", "+3V3"), ("1", "GND"), ("2", "GND"), ("11", "GND"), ("14", "GND"),
        ("8", "EN_C3"), ("23", "BOOT"),
        ("22", "LED_DI_3V3"),  # GPIO8 DI — SPI-ish ~10 MHz in FW (strap: 10k pull-up R3)
        ("18", "LED_CI_3V3"),  # GPIO4 CI
        ("19", "HALL_IN"),     # GPIO5 — once-per-rev index
        ("5", "C3_GPIO2"),     # strap: 10k pull-up R4
        # Programming access (v0.5 had none): UART0 on J2, native USB on TP5/TP6
        ("30", "C3_RXD"), ("31", "C3_TXD"),
        ("26", "C3_USB_DN"), ("27", "C3_USB_DP"),
    ]:
        if pn in pos:
            parts.append(connect_label_to_pin(net, pos[pn]))
            used.add(pn)
    for pn, xyz in pos.items():
        if pn in used:
            continue
        try:
            n = int(pn)
        except ValueError:
            n = -1
        if n >= 36:
            parts.append(connect_label_to_pin("GND", xyz))
            used.add(pn)
        else:
            parts.append(noconnect(xyz[0], xyz[1]))

    # U2 ME6211 — 500 mA; C3 Wi-Fi peaks ~335 mA → OK with ceramic bulk (see docs)
    u2 = (100.0, 50.8)
    me = resolve_symbol("ME6211C33M5")
    parts.append(instance("ME6211C33M5", "U2", "ME6211C33M5G-N", u2[0], u2[1], pin_numbers(me), FP["ME6211C33M5"]))
    mep = pin_positions(me, "ME6211C33M5", u2)
    for pn, net in [("1", "+5V"), ("2", "GND"), ("3", "+5V"), ("5", "+3V3")]:
        if pn in mep:
            parts.append(connect_label_to_pin(net, mep[pn]))
    if "4" in mep:
        parts.append(noconnect(mep["4"][0], mep["4"][1]))

    # U3 74AHCT125
    ah = resolve_symbol("74AHCT125")
    ah_pins = pin_numbers(ah)
    u3 = (150.0, 40.64)
    parts.append(instance("74AHCT125", "U3", "SN74AHCT125PWR", u3[0], u3[1], ah_pins, FP["74AHCT125"], unit=1))
    parts.append(instance("74AHCT125", "U3", "SN74AHCT125PWR", 150.0, 60.96, ah_pins, FP["74AHCT125"], unit=2))
    parts.append(instance("74AHCT125", "U3", "SN74AHCT125PWR", 150.0, 81.28, ah_pins, FP["74AHCT125"], unit=5))
    ah_pos1 = pin_positions(ah, "74AHCT125", u3)
    for pn, net in [("1", "GND"), ("2", "LED_DI_3V3"), ("3", "LED_DI")]:
        if pn in ah_pos1:
            parts.append(connect_label_to_pin(net, ah_pos1[pn]))
    ah_pos2 = pin_positions(ah, "74AHCT125", (150.0, 60.96))
    for pn, net in [("4", "GND"), ("5", "LED_CI_3V3"), ("6", "LED_CI")]:
        if pn in ah_pos2:
            parts.append(connect_label_to_pin(net, ah_pos2[pn]))
    ah_pos5 = pin_positions(ah, "74AHCT125", (150.0, 81.28))
    for pn, net in [("14", "+5V"), ("7", "GND")]:
        if pn in ah_pos5:
            parts.append(connect_label_to_pin(net, ah_pos5[pn]))
    parts.append(instance("74AHCT125", "U3", "SN74AHCT125PWR", 180.0, 40.64, ah_pins, FP["74AHCT125"], unit=3))
    parts.append(instance("74AHCT125", "U3", "SN74AHCT125PWR", 180.0, 60.96, ah_pins, FP["74AHCT125"], unit=4))
    # Unused gates: OE high (output disabled), input low, output open — no floating CMOS inputs
    for origin, y_pin, a_pin, oe_pin in [((180.0, 40.64), "8", "9", "10"), ((180.0, 60.96), "11", "12", "13")]:
        p = pin_positions(ah, "74AHCT125", origin)
        parts.append(noconnect(p[y_pin][0], p[y_pin][1]))
        parts.append(connect_label_to_pin("GND", p[a_pin]))
        parts.append(connect_label_to_pin("+5V", p[oe_pin]))

    # U4 DRV5023 hall — VCC=1, OUT=2 (OD), GND=3; pull-up on OUT.
    # v0.5 used AH1806 (micropower, duty-cycled sampling) — it misses a magnet that
    # passes in ~1 ms at 1200 RPM. DRV5023 samples continuously (~30 kHz).
    u4 = (100.0, 30.48)
    hall = resolve_symbol("DRV5023")
    parts.append(instance("DRV5023", "U4", "DRV5023FAQDBZR", u4[0], u4[1], pin_numbers(hall), FP["DRV5023"]))
    hp = pin_positions(hall, "DRV5023", u4)
    for pn, net in [("1", "+3V3"), ("2", "HALL_IN"), ("3", "GND")]:
        if pn in hp:
            parts.append(connect_label_to_pin(net, hp[pn]))
    two_pin("R", "R2", "10k", (120.0, 30.48), FP["R"], "HALL_IN", "+3V3")

    # APA102 chain
    def place_led(ref, xy, di, ci, do, co):
        led = resolve_symbol("APA102-2020")
        parts.append(instance("APA102-2020", ref, "APA102-2020", xy[0], xy[1], pin_numbers(led), FP["APA102-2020"]))
        p = pin_positions(led, "APA102-2020", xy)
        for pn, net in [("4", di), ("5", ci), ("1", "+5V"), ("6", "GND"), ("3", do), ("2", co)]:
            if pn in p:
                parts.append(connect_label_to_pin(net, p[pn]))

    place_led("D1", (50.0, 110.0), "LED_DI", "LED_CI", "LED_DO_1", "LED_CO_1")
    parts.append(text(50, 100, f"... {led_count - 2} x APA102-2020 daisy-chain (balanced bar, both sides of hub) ...", 1.2))
    led = resolve_symbol("APA102-2020")
    last_xy = (120.0, 110.0)
    parts.append(instance("APA102-2020", f"D{led_count}", "APA102-2020", last_xy[0], last_xy[1], pin_numbers(led), FP["APA102-2020"]))
    lp = pin_positions(led, "APA102-2020", last_xy)
    for pn, net in [("4", f"LED_DO_{led_count-1}"), ("5", f"LED_CO_{led_count-1}"), ("1", "+5V"), ("6", "GND")]:
        if pn in lp:
            parts.append(connect_label_to_pin(net, lp[pn]))
    for pn in ("3", "2"):
        if pn in lp:
            parts.append(noconnect(lp[pn][0], lp[pn][1]))
    if led_count >= 2:
        place_led("D2", (85.0, 110.0), "LED_DO_1", "LED_CO_1", "LED_DO_2", "LED_CO_2")

    for i in range(9):
        two_pin("C", f"Cd{i+1}", "100nF", (50 + i * 12, 140), FP["C"], "+5V", "GND")

    two_pin("C", "C1", "100nF", (100, 70), FP["C"], "+3V3", "GND")
    two_pin("C", "C2", "22uF", (110, 70), FP["C0805"], "+3V3", "GND")  # bulk for Wi-Fi peaks
    two_pin("C", "C3", "22uF", (120, 70), FP["C0805"], "+5V", "GND")
    two_pin("C", "C4", "10uF", (130, 70), FP["C0805"], "+5V", "GND")
    # >=470uF bulk on rotor +5V (Chief #4): 2× 330 µF 10 V polymer tantalum (low
    # profile, no wet electrolyte under ~120 g at the bar tip) instead of a 10×10 can.
    two_pin("C_Polarized", "C5", "330uF 10V polymer", (145, 70), FP["CPOLY"], "+5V", "GND")
    two_pin("C_Polarized", "C7", "330uF 10V polymer", (145, 90), FP["CPOLY"], "+5V", "GND")
    # TVS on +5V. KiCad SMAJ symbol: pin 1 = cathode (= D_SMA pad 1 / band).
    # v0.5 had pin 1 on GND → TVS forward-biased across the rail (dead short).
    two_pin("SMAJ5.0A", "D40", "SMAJ5.0A", (160, 70), FP["SMAJ5.0A"], "+5V", "GND")

    two_pin("R", "R1", "10k", (90, 70), FP["R"], "EN_C3", "+3V3")
    two_pin("C", "C6", "1uF", (90, 90), FP["C"], "EN_C3", "GND")  # EN RC delay per Espressif HW guide
    two_pin("R", "R3", "10k", (70, 90), FP["R"], "LED_DI_3V3", "+3V3")  # GPIO8 strap high
    two_pin("R", "R4", "10k", (80, 90), FP["R"], "C3_GPIO2", "+3V3")    # GPIO2 strap high
    two_pin("SW_Push", "SW1", "BOOT", (80, 70), FP["SW"], "BOOT", "GND")

    # Programming header: 3V3 GND EN IO9 TX RX (USB-UART adapter with auto-reset)
    c6 = resolve_symbol("Conn_01x06")
    parts.append(instance("Conn_01x06", "J2", "PROG", 20, 90, pin_numbers(c6), FP["HDR6"]))
    jp6 = pin_positions(c6, "Conn_01x06", (20, 90))
    for pn, net in [("1", "+3V3"), ("2", "GND"), ("3", "EN_C3"), ("4", "BOOT"), ("5", "C3_TXD"), ("6", "C3_RXD")]:
        parts.append(connect_label_to_pin(net, jp6[pn]))
    # Native-USB pogo pads (D-/D+) for flashing / JTAG without the header fitted
    tpu = resolve_symbol("TestPoint")
    for ref, xy, net in [("TP5", (100, 250), "C3_USB_DN"), ("TP6", (115, 250), "C3_USB_DP")]:
        parts.append(instance("TestPoint", ref, net, xy[0], xy[1], pin_numbers(tpu), "TestPoint:TestPoint_Pad_D1.0mm"))
        parts.append(connect_label_to_pin(net, pin_positions(tpu, "TestPoint", xy)["1"]))

    # Slip ring
    c = resolve_symbol("Conn_01x04")
    parts.append(instance("Conn_01x04", "J1", "SLIP_5V", 20, 50.8, pin_numbers(c), FP["HDR4"]))
    jp = pin_positions(c, "Conn_01x04", (20, 50.8))
    for pn, net in [("1", "+5V"), ("2", "GND"), ("3", "GND"), ("4", "+5V")]:
        if pn in jp:
            parts.append(connect_label_to_pin(net, jp[pn]))

    # Balance trim pads (solder-weight copper) — electrically GND
    tp = resolve_symbol("TestPoint")
    # Keep clear of LED grid (APA102 VDD stubs extend ~8mm above each LED).
    for i, xy in enumerate([(25, 250), (40, 250), (230, 250), (245, 250)], 1):
        parts.append(instance("TestPoint", f"TP{i}", "BAL_PAD", xy[0], xy[1], pin_numbers(tp), FP["TP"]))
        tpos = pin_positions(tp, "TestPoint", xy)
        if "1" in tpos:
            parts.append(connect_label_to_pin("GND", tpos["1"]))

    pwr_counter = [pwr_i]
    drive_net(parts, pwr_counter, "+5V", 15.24, 20.32, with_flag=True)
    drive_net(parts, pwr_counter, "+3V3", 30.48, 20.32, with_flag=False)
    drive_net(parts, pwr_counter, "GND", 45.72, 20.32, with_flag=True)

    parts.append(text(10, 10, f"POV Clock Minute Bar — {which} ({length_mm}mm balanced, {led_count}x APA102)", 2.0))
    parts.append(text(10, 15, "v0.6: DRV5023 index; 660uF polymer + TVS on 5V; UART/USB programming; ESP-NOW frames only; SPI 8-12 MHz", 1.1))

    prev_do, prev_co = "LED_DO_2", "LED_CO_2"
    for i in range(3, led_count):
        do, co = f"LED_DO_{i}", f"LED_CO_{i}"
        # 30 mm × 35 mm pitch: v0.5's 15 × 25 mm grid let neighbouring pin stubs overlap
        xy = (250 + ((i - 3) % 8) * 30, 40 + ((i - 3) // 8) * 35)
        place_led(f"D{i}", xy, prev_do, prev_co, do, co)
        prev_do, prev_co = do, co

    body = sch_header(f"POV Clock Minute Bar ({which}, {length_mm}mm, {led_count}x APA102)", paper="A2")
    body = body.replace('(rev "0.2")', '(rev "0.6")')
    body += lib_symbols_section(syms) + "\n"
    body += "".join(parts)
    body += sch_footer()
    write(outdir / f"{name}.kicad_sch", body)
    write_pro(outdir / f"{name}.kicad_pro", name)
    return name


# =========================================================================
# Minimal PCB outlines (placement done by place_and_route.py)
# =========================================================================
def load_mod(lib_pretty: str, mod_name: str) -> str | None:
    candidates = [
        KICAD_FP / f"{lib_pretty}.pretty" / f"{mod_name}.kicad_mod",
        ROOT / "hardware" / "libs" / f"{lib_pretty}.pretty" / f"{mod_name}.kicad_mod",
    ]
    for c in candidates:
        if c.exists():
            return c.read_text()
    hits = list(KICAD_FP.glob(f"**/{mod_name}.kicad_mod"))
    if hits:
        return hits[0].read_text()
    return None

def embed_footprint(mod_text: str, ref: str, value: str, x: float, y: float, rot: int = 0) -> str:
    text = mod_text
    text = re.sub(r'\(version [^\)]+\)', '', text, count=1)
    text = re.sub(r'\(generator [^\)]+\)', '', text, count=1)
    text = re.sub(r'\(generator_version [^\)]+\)', '', text, count=1)
    text = text.strip()
    text = re.sub(r'\(layer "[^"]+"\)', '(layer "F.Cu")', text, count=1)
    if "(at " in text:
        text = re.sub(r'\(at [^\)]+\)', f'(at {x:.3f} {y:.3f} {rot})', text, count=1)
    else:
        text = text.replace('(layer "F.Cu")', f'(layer "F.Cu")\n\t\t(at {x:.3f} {y:.3f} {rot})', 1)
    text = re.sub(r'\(property "Reference" "[^"]*"', f'(property "Reference" "{ref}"', text, count=1)
    text = re.sub(r'\(property "Value" "[^"]*"', f'(property "Value" "{value}"', text, count=1)
    text = re.sub(r'\(uuid "[^"]+"\)', lambda m: f'(uuid "{uid()}")', text)
    if "(uuid" not in text[:200]:
        text = text.replace('(layer "F.Cu")', f'(layer "F.Cu")\n\t\t(uuid "{uid()}")', 1)
    return "\t" + text.replace("\n", "\n\t") + "\n"

LAYERS = '''\t(layers
\t\t(0 "F.Cu" signal)
\t\t(31 "B.Cu" signal)
\t\t(32 "B.Adhes" user "B.Adhesive")
\t\t(33 "F.Adhes" user "F.Adhesive")
\t\t(34 "B.Paste" user)
\t\t(35 "F.Paste" user)
\t\t(36 "B.SilkS" user "B.Silkscreen")
\t\t(37 "F.SilkS" user "F.Silkscreen")
\t\t(38 "B.Mask" user)
\t\t(39 "F.Mask" user)
\t\t(40 "Dwgs.User" user "User.Drawings")
\t\t(41 "Cmts.User" user "User.Comments")
\t\t(42 "Eco1.User" user "User.Eco1")
\t\t(43 "Eco2.User" user "User.Eco2")
\t\t(44 "Edge.Cuts" user)
\t\t(45 "Margin" user)
\t\t(46 "B.CrtYd" user "B.Courtyard")
\t\t(47 "F.CrtYd" user "F.Courtyard")
\t\t(48 "B.Fab" user)
\t\t(49 "F.Fab" user)
\t)
'''

def pcb_header(title: str) -> str:
    return f'''(kicad_pcb
\t(version {PCB_VER})
\t(generator "clockor_rebuild")
\t(generator_version "1.0")
\t(general
\t\t(thickness 1.6)
\t\t(legacy_teardrops no)
\t)
\t(paper "A4")
\t(title_block
\t\t(title "{title}")
\t\t(date "{DATE}")
\t\t(rev "0.5")
\t\t(company "Jason / clockor")
\t\t(comment 1 "Hybrid v0.3 — placed; route via Freerouting")
\t)
{LAYERS}
\t(setup
\t\t(pad_to_mask_clearance 0.05)
\t\t(allow_soldermask_bridges_in_footprints no)
\t)
\t(net 0 "")
'''

def build_base_pcb(outdir: Path):
    nets = ["", "GND", "VIN_12V", "+5V", "+3V3", "USB_D+", "USB_D-", "I2C0_SDA", "I2C0_SCL"]
    body = pcb_header("POV Clock Base Controller Hybrid")
    for i, n in enumerate(nets):
        if i == 0:
            continue
        body += f'\t(net {i} "{n}")\n'
    body += f'''\t(gr_rect
\t\t(start 0 0) (end 120 90)
\t\t(stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts")
\t\t(uuid "{uid()}")
\t)
'''
    placements = [
        ("RF_Module", "ESP32-S3-WROOM-1", "U1", "ESP32-S3-WROOM-1-N16R8", 30, 55),
        ("Package_TO_SOT_SMD", "TO-263-5_TabPin3", "U2", "XL4015E1", 35, 15),
        ("Package_TO_SOT_SMD", "SOT-223-3_TabPin2", "U3", "AMS1117-3.3", 80, 15),
        ("Package_SO", "HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.5mm_ThermalVias", "U5", "DRV8313", 95, 35),
        ("Package_SO", "SOIC-16_3.9x9.9mm_P1.27mm", "U4", "ULN2003A", 95, 65),
        ("Connector_USB", "USB_C_Receptacle_HRO_TYPE-C-31-M-12", "J2", "USB-C", 15, 45),
    ]
    for lib, mod, ref, val, x, y in placements:
        mt = load_mod(lib, mod)
        if not mt:
            print("MISSING FP", lib, mod)
            continue
        body += embed_footprint(mt, ref, val, x, y)
    body += ")\n"
    write(outdir / "base-controller.kicad_pcb", body)

def build_hand_pcb(outdir: Path, which: str, length_mm: int, led_count: int):
    """Centered balanced bar: hub in middle, LEDs both sides."""
    body = pcb_header(f"POV Clock Minute Bar ({which})")
    body += '\t(net 1 "GND")\n\t(net 2 "+5V")\n\t(net 3 "+3V3")\n'
    hub_w, arm_w = 28.0, 12.0
    half = float(length_mm) / 2.0
    total_l = float(length_mm)
    # Wide hub rectangle (simplified)
    body += f'''\t(gr_rect
\t\t(start 0 0) (end {total_l:.2f} {hub_w:.2f})
\t\t(stroke (width 0.1) (type default)) (fill none) (layer "Edge.Cuts")
\t\t(uuid "{uid()}")
\t)
'''
    cx, cy = total_l / 2.0, hub_w / 2.0
    mt = load_mod("Espressif", "ESP32-C3-MINI-1")
    if mt:
        body += embed_footprint(mt, "U1", "ESP32-C3-MINI-1-N4", cx, cy - 4)
    for lib, mod, ref, val, x, y in [
        ("Package_TO_SOT_SMD", "SOT-23-5", "U2", "ME6211C33M5", cx - 8, cy + 8),
        ("Package_SO", "TSSOP-14_4.4x5mm_P0.65mm", "U3", "74AHCT125", cx + 8, cy + 8),
        ("Package_TO_SOT_SMD", "SC-59", "U4", "AH1806-W", cx, cy + 10),
    ]:
        m = load_mod(lib, mod)
        if m:
            body += embed_footprint(m, ref, val, x, y)
    led_mod = load_mod("LED_SMD", "LED-APA102-2020")
    if led_mod:
        # 18 LEDs each side of hub center
        n_side = led_count // 2
        for i in range(n_side):
            # left arm (negative X from center)
            body += embed_footprint(led_mod, f"D{i+1}", "APA102-2020", cx - 8 - i * 3.5, cy, 0)
        for i in range(n_side):
            body += embed_footprint(led_mod, f"D{n_side+i+1}", "APA102-2020", cx + 8 + i * 3.5, cy, 0)
    # Balance pads at tips
    tp = load_mod("TestPoint", "TestPoint_Pad_D2.5mm")
    if tp:
        body += embed_footprint(tp, "TP1", "BAL_PAD", 3, cy)
        body += embed_footprint(tp, "TP2", "BAL_PAD", total_l - 3, cy)
    body += ")\n"
    write(outdir / f"hand-{which}.kicad_pcb", body)


def verify(sch: Path) -> int:
    """Fail the build on label/pin collisions, floating pins or undriven power nets."""
    from sch_netcheck import check
    problems = [p for p in check(sch) if not p.startswith("SINGLE")]
    for p in problems:
        print("  ✗", p)
    print(f"verify {sch.name}: {len(problems)} problem(s)")
    return len(problems)


def main():
    import argparse
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sch-only", action="store_true",
                    help="regenerate schematics/projects only; keep the existing .kicad_pcb layouts "
                         "(then use pcbnew 'Update PCB from Schematic' to pull changes in)")
    args = ap.parse_args()
    global KEEP_EXISTING_PRO
    KEEP_EXISTING_PRO = args.sch_only

    base = HW / "base-controller"
    minute = HW / "hand-minute"
    # Remove obsolete hour rotor board
    hour = HW / "hand-hour"
    if hour.exists():
        shutil.rmtree(hour)
        print("removed obsolete hand-hour/")

    for d in (base, minute):
        if d.exists() and not args.sch_only:
            shutil.rmtree(d)
        d.mkdir(parents=True, exist_ok=True)

    sym_libs = [
        ("Clockor", "${KIPRJMOD}/../libs/Clockor.kicad_sym"),
        ("Espressif", "${KIPRJMOD}/../libs/Espressif.kicad_sym"),
    ]
    fp_libs = [
        ("Espressif", "${KIPRJMOD}/../libs/Espressif.pretty"),
        ("Clockor", "${KIPRJMOD}/../libs/Clockor.pretty"),
    ]
    for d in (base, minute):
        write_sym_lib_table(d / "sym-lib-table", sym_libs)
        write_fp_lib_table(d / "fp-lib-table", fp_libs)

    build_base_sch(base)
    # Balanced diametric bar ~160 mm, 36 LEDs (18 per side)
    build_hand_sch(minute, "minute", 160, 36)
    if not args.sch_only:
        build_base_pcb(base)
        build_hand_pcb(minute, "minute", 160, 36)
    bad = verify(base / "base-controller.kicad_sch") + verify(minute / "hand-minute.kicad_sch")
    if bad:
        raise SystemExit(f"schematic verification failed ({bad} problems)")
    print("DONE rebuild hybrid v0.6")


if __name__ == "__main__":
    main()
