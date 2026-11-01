#!/usr/bin/env python3
"""Parametric two-hand POV clock mechanical assembly (CadQuery).
Defaults match PCB design notes: minute 150 mm, hour 120 mm.
Adds clock-face dial with 12 hour markers (12/3/6/9 emphasized),
LED pads along hands, and two poses:
  - Clock mode (static): ~10:10 (minute at 2, hour ~10:10)
  - POV mode: hands locked 180° apart
Dimensions labeled ESTIMATE where not from a datasheet.
"""
from pathlib import Path
import math
import cadquery as cq
from cadquery import exporters

OUT = Path("/workspace/pov-clock-pcb/renders/mech")
CAD = Path("/workspace/pov-clock-pcb/cad")
OUT.mkdir(parents=True, exist_ok=True)
CAD.mkdir(parents=True, exist_ok=True)

# --- Key dims (mm) — ESTIMATE unless noted ---
BASE_OD = 180.0          # ESTIMATE enclosure / base OD
BASE_H = 18.0
PLATE_TH = 4.0
ENCL_H = 55.0            # clear dome height ESTIMATE
ENCL_TH = 2.5
MINUTE_LEN = 150.0       # design default
HOUR_LEN = 120.0
ARM_W = 10.0
ARM_TH = 1.6
HUB_R = 14.0
INNER_SHAFT_D = 6.0      # solid minute shaft ESTIMATE
OUTER_TUBE_OD = 12.0     # hour tube ESTIMATE
OUTER_TUBE_ID = 8.0
SHAFT_LEN = 95.0
BEARING_OD = 16.0
BEARING_ID = 6.0
BEARING_H = 5.0
MOTOR_OD = 28.0          # gimbal BLDC stub ESTIMATE (e.g. 2804-class)
MOTOR_H = 18.0
MOTOR_OFFSET = 55.0      # belt drive offset from axis
PULLEY_OD = 20.0
SLIP_OD = 22.0
SLIP_H = 12.0
MAGNET_D = 6.0
MAGNET_H = 2.5
ENC_BOARD = 18.0
DIAL_ID = 40.0
DIAL_OD = BASE_OD - 18.0
MARKER_INNER = DIAL_OD / 2 - 14.0
MARKER_OUTER = DIAL_OD / 2 - 2.0
LED_PITCH = 3.5
LED_SIZE = 2.0
LED_H = 0.9
N_LED_MIN = 36
N_LED_HOUR = 30

# Clock angles: 0° = 12 o'clock, positive = clockwise.
# CadQuery hand arm is built along +X (3 o'clock = 90° CW from 12).
def clock_to_cq(deg_cw_from_12: float) -> float:
    """Map clock degrees (CW from 12) to CQ rotate about +Z from +X arm."""
    return deg_cw_from_12 - 90.0

# 10:10 pose: minute at 2 (= 60°), hour at 10:10 (= 10*30 + 10*0.5 = 305°)
MINUTE_CLOCK_DEG = 60.0
HOUR_CLOCK_DEG = 305.0
# POV: locked 180° apart — minute at 12, hour at 6
POV_MINUTE_DEG = 0.0
POV_HOUR_DEG = 180.0

def cyl(d, h, z0=0):
    return cq.Workplane("XY").workplane(offset=z0).circle(d / 2).extrude(h)

def tube(od, id_, h, z0=0):
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .circle(od / 2)
        .circle(id_ / 2)
        .extrude(h)
    )

def hand_blank(length, z):
    hub = cyl(HUB_R * 2, ARM_TH, z)
    arm = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(length / 2, 0)
        .rect(length, ARM_W)
        .extrude(ARM_TH)
    )
    return hub.union(arm)

def led_row(length, n_led, z, clock_deg):
    """Small LED cubes along the arm (glowing hand representation in CAD)."""
    # first LED starts just past hub
    start = HUB_R + 4.0
    usable = length - start - 4.0
    pitch = usable / max(n_led - 1, 1)
    ang = clock_to_cq(clock_deg)
    shape = None
    for i in range(n_led):
        r = start + i * pitch
        led = (
            cq.Workplane("XY")
            .workplane(offset=z + ARM_TH)
            .center(r, 0)
            .rect(LED_SIZE, LED_SIZE)
            .extrude(LED_H)
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        shape = led if shape is None else shape.union(led)
    return shape

def hand(length, z, clock_deg, n_led):
    blank = hand_blank(length, z).rotate((0, 0, 0), (0, 0, 1), clock_to_cq(clock_deg))
    leds = led_row(length, n_led, z, clock_deg)
    return blank.union(leds)

def dial_face(z=PLATE_TH + 0.2):
    """Clock dial ring with 12 hour markers; 12/3/6/9 emphasized."""
    ring = tube(DIAL_OD, DIAL_ID, 1.2, z)
    markers = None
    for h in range(12):
        ang = clock_to_cq(h * 30.0)  # marker at hour h
        major = h % 3 == 0
        w = 4.0 if major else 2.0
        thick = 2.8 if major else 1.6
        # radial marker as thin box from MARKER_INNER to MARKER_OUTER
        mid_r = (MARKER_INNER + MARKER_OUTER) / 2
        length = MARKER_OUTER - MARKER_INNER
        m = (
            cq.Workplane("XY")
            .workplane(offset=z + 1.2)
            .center(mid_r, 0)
            .rect(length, w)
            .extrude(thick)
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        markers = m if markers is None else markers.union(m)
    # center hub ring accent
    hub_ring = tube(HUB_R * 2 + 6, HUB_R * 2 + 1, 1.0, z + 1.2)
    return ring.union(markers).union(hub_ring)

def bearing(z):
    return tube(BEARING_OD, BEARING_ID, BEARING_H, z)

def motor_at(x, y, z):
    body = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(x, y)
        .circle(MOTOR_OD / 2)
        .extrude(MOTOR_H)
    )
    shaft = (
        cq.Workplane("XY")
        .workplane(offset=z + MOTOR_H)
        .center(x, y)
        .circle(2)
        .extrude(8)
    )
    return body.union(shaft)

def pulley(x, y, z):
    return (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(x, y)
        .circle(PULLEY_OD / 2)
        .extrude(6)
    )

def belt_approx(x1, y1, x2, y2, z, w=4):
    mx, my = (x1 + x2) / 2, (y1 + y2) / 2
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy)
    ang = math.degrees(math.atan2(dy, dx))
    return (
        cq.Workplane("XY")
        .workplane(offset=z)
        .transformed(offset=(mx, my, 0), rotate=(0, 0, ang))
        .rect(L, w)
        .extrude(1.5)
    )

def build_common():
    base = cyl(BASE_OD, BASE_H, -BASE_H)
    plate = cyl(BASE_OD - 10, PLATE_TH, 0)
    minute_shaft = cyl(INNER_SHAFT_D, SHAFT_LEN, -20)
    hour_tube = tube(OUTER_TUBE_OD, OUTER_TUBE_ID, SHAFT_LEN - 15, -15)
    b1 = bearing(5)
    b2 = bearing(25)
    slip_inner = tube(SLIP_OD, OUTER_TUBE_OD + 0.5, SLIP_H, -8)
    slip_outer = tube(SLIP_OD + 6, SLIP_OD + 0.5, SLIP_H, -8)
    mag_m = cyl(MAGNET_D, MAGNET_H, -18)
    mag_h = tube(MAGNET_D + 4, MAGNET_D + 1, MAGNET_H, -18)
    enc_m = (
        cq.Workplane("XY")
        .workplane(offset=-22)
        .center(0, 22)
        .rect(ENC_BOARD, ENC_BOARD)
        .extrude(1.2)
    )
    enc_h = (
        cq.Workplane("XY")
        .workplane(offset=-22)
        .center(0, -22)
        .rect(ENC_BOARD, ENC_BOARD)
        .extrude(1.2)
    )
    m1 = motor_at(MOTOR_OFFSET, 0, -BASE_H)
    m2 = motor_at(-MOTOR_OFFSET, 0, -BASE_H)
    p_m1 = pulley(MOTOR_OFFSET, 0, MOTOR_H - BASE_H + 2)
    p_m2 = pulley(-MOTOR_OFFSET, 0, MOTOR_H - BASE_H + 2)
    p_axis_m = pulley(0, 0, MOTOR_H - BASE_H + 2)
    belt1 = belt_approx(MOTOR_OFFSET, 0, 0, 0, MOTOR_H - BASE_H + 4)
    belt2 = belt_approx(-MOTOR_OFFSET, 0, 0, 8, MOTOR_H - BASE_H + 8)
    encl = tube(BASE_OD - 4, BASE_OD - 4 - 2 * ENCL_TH, ENCL_H, PLATE_TH)
    dial = dial_face()
    return (
        base.union(plate)
        .union(minute_shaft)
        .union(hour_tube)
        .union(b1)
        .union(b2)
        .union(slip_inner)
        .union(slip_outer)
        .union(mag_m)
        .union(mag_h)
        .union(enc_m)
        .union(enc_h)
        .union(m1)
        .union(m2)
        .union(p_m1)
        .union(p_m2)
        .union(p_axis_m)
        .union(belt1)
        .union(belt2)
        .union(encl)
        .union(dial)
    )

def build_pose(minute_deg, hour_deg):
    common = build_common()
    minute_hand = hand(MINUTE_LEN, 42, minute_deg, N_LED_MIN)
    hour_hand = hand(HOUR_LEN, 38, hour_deg, N_LED_HOUR)
    return common.union(minute_hand).union(hour_hand)

# Clock mode (static) ~10:10
assy_clock = build_pose(MINUTE_CLOCK_DEG, HOUR_CLOCK_DEG)
# POV mode — hands 180° apart
assy_pov = build_pose(POV_MINUTE_DEG, POV_HOUR_DEG)
# Default assembly = clock mode (readable static time)
assy = assy_clock

# Exploded: shift motors/enclosure/hands along Z and X (clock pose)
minute_hand_x = hand(MINUTE_LEN, 42, MINUTE_CLOCK_DEG, N_LED_MIN)
hour_hand_x = hand(HOUR_LEN, 38, HOUR_CLOCK_DEG, N_LED_HOUR)
base = cyl(BASE_OD, BASE_H, -BASE_H)
plate = cyl(BASE_OD - 10, PLATE_TH, 0)
minute_shaft = cyl(INNER_SHAFT_D, SHAFT_LEN, -20)
hour_tube = tube(OUTER_TUBE_OD, OUTER_TUBE_ID, SHAFT_LEN - 15, -15)
b1 = bearing(5)
b2 = bearing(25)
slip_inner = tube(SLIP_OD, OUTER_TUBE_OD + 0.5, SLIP_H, -8)
slip_outer = tube(SLIP_OD + 6, SLIP_OD + 0.5, SLIP_H, -8)
m1 = motor_at(MOTOR_OFFSET, 0, -BASE_H)
m2 = motor_at(-MOTOR_OFFSET, 0, -BASE_H)
encl = tube(BASE_OD - 4, BASE_OD - 4 - 2 * ENCL_TH, ENCL_H, PLATE_TH)
dial = dial_face()
exploded = (
    base.union(plate)
    .union(dial.translate((0, 0, 15)))
    .union(minute_shaft.translate((0, 0, 30)))
    .union(hour_tube.translate((0, 0, 20)))
    .union(b1.translate((0, 0, 40)))
    .union(b2.translate((0, 0, 50)))
    .union(minute_hand_x.translate((0, 0, 70)))
    .union(hour_hand_x.translate((0, 0, 60)))
    .union(slip_inner.translate((40, 0, 0)))
    .union(slip_outer.translate((55, 0, 0)))
    .union(m1.translate((25, 0, -20)))
    .union(m2.translate((-25, 0, -20)))
    .union(encl.translate((0, 0, 90)))
)

half = cq.Workplane("XY").box(
    BASE_OD * 1.2, BASE_OD * 1.2, 200, centered=(True, False, True)
)
section = assy.intersect(half.translate((0, -BASE_OD * 0.6, 20)))

# Export STEP/STL
exporters.export(assy, str(CAD / "pov_clock_assembly.step"))
exporters.export(assy, str(CAD / "pov_clock_assembly.stl"))
exporters.export(assy_clock, str(CAD / "pov_clock_clock_mode.stl"))
exporters.export(assy_pov, str(CAD / "pov_clock_pov_mode.stl"))
exporters.export(exploded, str(CAD / "pov_clock_exploded.stl"))
exporters.export(section, str(CAD / "pov_clock_section.stl"))

opts = {
    "width": 900,
    "height": 700,
    "marginLeft": 40,
    "marginTop": 40,
    "showAxes": False,
    "strokeWidth": 0.35,
}

def export_svg(shape, name, projectionDir=(1, 1, 1)):
    exporters.export(
        shape,
        str(OUT / name),
        exportType=exporters.ExportTypes.SVG,
        opt={
            **opts,
            "projectionDir": projectionDir,
            "strokeColor": (30, 30, 40),
            "hiddenColor": (180, 180, 190),
            "showHidden": False,
        },
    )

export_svg(assy_clock, "iso.svg", (1.2, -1.5, 1.0))
export_svg(assy_clock, "clock_iso.svg", (1.2, -1.5, 1.0))
export_svg(assy_clock, "clock_front.svg", (0, 0, 1))  # top-down front of dial
export_svg(assy_pov, "pov_iso.svg", (1.2, -1.5, 1.0))
export_svg(assy_pov, "pov_front.svg", (0, 0, 1))
export_svg(exploded, "exploded.svg", (1.2, -1.5, 1.0))
export_svg(section, "section.svg", (0.2, -1.0, 0.15))
export_svg(assy_clock, "front.svg", (0, -1, 0))
print("CAD exports OK — clock 10:10 + POV 180° + dial markers")
for p in sorted(CAD.glob("*")) + sorted(OUT.glob("*.svg")):
    print(p.name, p.stat().st_size)
