"""Pin-accurate DRV8313 (HTSSOP-28 / PWP) symbol — not in stock KiCad libs."""
from pathlib import Path

# PWP pinout from TI SLVSBA5D
# Left side (1-14 bottom to... standard: pin1 top-left going down)
# We'll place logically: inputs left, power/outputs right

LEFT = [
    # (num, name, type)
    ("27", "IN1", "input"),
    ("26", "EN1", "input"),
    ("25", "IN2", "input"),
    ("24", "EN2", "input"),
    ("23", "IN3", "input"),
    ("22", "EN3", "input"),
    ("17", "nSLEEP", "input"),
    ("16", "nRESET", "input"),
    ("12", "COMPP", "input"),
    ("13", "COMPN", "input"),
]
RIGHT = [
    ("5", "OUT1", "output"),
    ("8", "OUT2", "output"),
    ("9", "OUT3", "output"),
    ("18", "nFAULT", "open_collector"),
    ("19", "nCOMPO", "open_collector"),
    ("4", "VM", "power_in"),
    ("11", "VM", "power_in"),
    ("15", "V3P3", "power_out"),
    ("3", "VCP", "passive"),
    ("2", "CPH", "passive"),
    ("1", "CPL", "passive"),
]
BOTTOM = [
    ("6", "PGND1", "power_in"),
    ("7", "PGND2", "power_in"),
    ("10", "PGND3", "power_in"),
    ("14", "GND", "power_in"),
    ("20", "GND", "power_in"),
    ("28", "GND", "power_in"),
    ("21", "NC", "no_connect"),
]
# Note: VM appears twice (pins 4 and 11) — same name OK in KiCad for power

def pin(num, name, typ, x, y, rot, length=2.54):
    return f'''\t\t\t(pin {typ} line
\t\t\t\t(at {x} {y} {rot})
\t\t\t\t(length {length})
\t\t\t\t(name "{name}"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t\t(number "{num}"
\t\t\t\t\t(effects
\t\t\t\t\t\t(font
\t\t\t\t\t\t\t(size 1.27 1.27)
\t\t\t\t\t\t)
\t\t\t\t\t)
\t\t\t\t)
\t\t\t)'''

def build():
    nL, nR, nB = len(LEFT), len(RIGHT), len(BOTTOM)
    h = max(nL, nR) * 2.54 + 5.08
    w = 25.4
    pins = []
    for i, (num, name, typ) in enumerate(LEFT):
        y = h/2 - 2.54*(i+1)
        pins.append(pin(num, name, typ, -w/2, round(y,2), 0))
    for i, (num, name, typ) in enumerate(RIGHT):
        y = h/2 - 2.54*(i+1)
        pins.append(pin(num, name, typ, w/2, round(y,2), 180))
    # bottom GND/PGND
    span = (nB-1)*2.54
    x0 = -span/2
    for i, (num, name, typ) in enumerate(BOTTOM):
        x = x0 + i*2.54
        pins.append(pin(num, name, typ, round(x,2), -h/2, 90))

    body = f'''(kicad_symbol_lib
\t(version 20241209)
\t(generator "clockor_drv8313")
\t(generator_version "1.0")
\t(symbol "DRV8313"
\t\t(exclude_from_sim no)
\t\t(in_bom yes)
\t\t(on_board yes)
\t\t(property "Reference" "U"
\t\t\t(at 0 {h/2+2.54:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Value" "DRV8313"
\t\t\t(at 0 {-h/2-2.54:.2f} 0)
\t\t\t(effects (font (size 1.27 1.27)))
\t\t)
\t\t(property "Footprint" "Package_SO:HTSSOP-28-1EP_4.4x9.7mm_P0.65mm_EP3.4x9.5mm_ThermalVias"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Datasheet" "https://www.ti.com/lit/ds/symlink/drv8313.pdf"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "Description" "2.5A 3-Phase Brushless DC Motor Driver, HTSSOP-28"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "ki_keywords" "BLDC motor driver FOC DRV8313"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(property "ki_fp_filters" "HTSSOP*28*"
\t\t\t(at 0 0 0)
\t\t\t(effects (font (size 1.27 1.27)) (hide yes))
\t\t)
\t\t(symbol "DRV8313_0_1"
\t\t\t(rectangle
\t\t\t\t(start {-w/2+2.54} {-h/2})
\t\t\t\t(end {w/2-2.54} {h/2})
\t\t\t\t(stroke (width 0.254) (type default))
\t\t\t\t(fill (type background))
\t\t\t)
\t\t)
\t\t(symbol "DRV8313_1_1"
{chr(10).join(pins)}
\t\t)
\t)
)
'''
    out = Path("/workspace/clockor/hardware/libs/Clockor.kicad_sym")
    out.write_text(body)
    print("wrote", out, "bytes", out.stat().st_size)

if __name__ == "__main__":
    build()
