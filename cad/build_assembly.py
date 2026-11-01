#!/usr/bin/env python3
"""Hybrid Clockor mechanical assembly (CadQuery) — Chief Round 2 / v0.4.

Minute = spinning POV bar on solid shaft (Furitek 2204).
Hour = off-axis 28BYJ-48 → belt/gear → thin hollow hour tube; hand only in front of clear dial.
AS5600 magnet on motor shaft REAR; Mercotac 205 on FRONT shaft end.
Axial gap bar-tip plane → dial underside >= 5 mm including hub runout budget.
"""
from pathlib import Path
import math
import cadquery as cq
from cadquery import exporters

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "renders" / "mech"
CAD = ROOT / "cad"
OUT.mkdir(parents=True, exist_ok=True)
CAD.mkdir(parents=True, exist_ok=True)

# --- Key dims (mm) — ESTIMATE unless LOCKED ---
BASE_OD = 180.0
BASE_H = 22.0
PLATE_TH = 4.0
ENCL_H = 60.0
ENCL_TH = 2.5
MINUTE_LEN = 150.0
HOUR_LEN = 110.0
ARM_W = 10.0
ARM_TH = 1.6
HUB_R = 14.0
INNER_SHAFT_D = 5.0          # solid minute shaft ESTIMATE
HOUR_TUBE_OD = 8.0           # thin hollow hour shaft ESTIMATE
HOUR_TUBE_ID = 5.8           # clears minute shaft + bushing
SHAFT_LEN = 100.0
BEARING_OD = 16.0
BEARING_ID = 5.0
BEARING_H = 5.0
MOTOR_OD = 28.0              # Furitek KOMODO 2204
MOTOR_H = 19.0
STEPPER_OFFSET = 48.0        # off-axis 28BYJ-48
STEPPER_BODY = 28.0
PULLEY_OD = 18.0
# Mercotac 205 approx body (catalog ~0.56" class for 2-conductor — ESTIMATE envelope)
SLIP_OD = 16.0
SLIP_H = 18.0
MAGNET_D = 6.0
MAGNET_H = 2.5
ENC_BOARD = 18.0
DIAL_ID = 36.0
DIAL_OD = BASE_OD - 18.0
DIAL_TH = 2.0                # clear acrylic / diffuser
MARKER_INNER = DIAL_OD / 2 - 14.0
MARKER_OUTER = DIAL_OD / 2 - 2.0
LED_SIZE = 2.0
LED_H = 0.9
N_LED_MIN = 36
# LOCKED Round 2
AXIAL_GAP_BAR_TO_DIAL = 5.0  # mm, includes hub runout budget
HUB_RUNOUT_BUDGET = 1.0      # portion of the 5 mm reserved for TIR

# Z stations (rear negative → front positive)
Z_MAG = -MOTOR_H - 8.0
Z_ENC = Z_MAG - 4.0
Z_MOTOR = -MOTOR_H
Z_PLATE = 0.0
Z_BEARING1 = 6.0
Z_BEARING2 = 22.0
Z_SLIP = 28.0
Z_HUB = Z_SLIP + SLIP_H + 2.0
Z_BAR = Z_HUB
Z_DIAL = Z_BAR + ARM_TH + LED_H + AXIAL_GAP_BAR_TO_DIAL
Z_HOUR_HAND = Z_DIAL + DIAL_TH + 1.0


def clock_to_cq(deg_cw_from_12: float) -> float:
    return deg_cw_from_12 - 90.0


MINUTE_CLOCK_DEG = 60.0
HOUR_CLOCK_DEG = 305.0
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


def hand_blank(length, z, both_sides=False):
    hub = cyl(HUB_R * 2, ARM_TH, z)
    if both_sides:
        arm_r = (
            cq.Workplane("XY")
            .workplane(offset=z)
            .center(length / 2, 0)
            .rect(length, ARM_W)
            .extrude(ARM_TH)
        )
        arm_l = (
            cq.Workplane("XY")
            .workplane(offset=z)
            .center(-length / 2, 0)
            .rect(length, ARM_W)
            .extrude(ARM_TH)
        )
        return hub.union(arm_r).union(arm_l)
    arm = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(length / 2, 0)
        .rect(length, ARM_W)
        .extrude(ARM_TH)
    )
    return hub.union(arm)


def led_row_balanced(length, n_led, z, clock_deg):
    """LEDs both sides of hub (hybrid minute bar)."""
    n_side = n_led // 2
    start = HUB_R + 4.0
    usable = length - start - 4.0
    pitch = usable / max(n_side - 1, 1)
    ang = clock_to_cq(clock_deg)
    shape = None
    for side in (+1, -1):
        for i in range(n_side):
            r = side * (start + i * pitch)
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


def minute_hand(length, z, clock_deg):
    blank = hand_blank(length, z, both_sides=True).rotate(
        (0, 0, 0), (0, 0, 1), clock_to_cq(clock_deg)
    )
    leds = led_row_balanced(length, N_LED_MIN, z, clock_deg)
    return blank.union(leds)


def hour_hand_only(length, z, clock_deg):
    """Thin physical hour hand — no LEDs — in front of dial only."""
    blank = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .moveTo(0, 0)
        .circle(6)
        .moveTo(length / 2, 0)
        .rect(length, 6)
        .extrude(1.2)
        .rotate((0, 0, 0), (0, 0, 1), clock_to_cq(clock_deg))
    )
    return blank


def dial_face(z):
    """Clear acrylic / diffuser dial with 12 markers (visualized opaque in CAD)."""
    ring = tube(DIAL_OD, DIAL_ID, DIAL_TH, z)
    markers = None
    for h in range(12):
        ang = clock_to_cq(h * 30.0)
        major = h % 3 == 0
        w = 4.0 if major else 2.0
        thick = 1.2 if major else 0.8
        mid_r = (MARKER_INNER + MARKER_OUTER) / 2
        length = MARKER_OUTER - MARKER_INNER
        m = (
            cq.Workplane("XY")
            .workplane(offset=z + DIAL_TH)
            .center(mid_r, 0)
            .rect(length, w)
            .extrude(thick)
            .rotate((0, 0, 0), (0, 0, 1), ang)
        )
        markers = m if markers is None else markers.union(m)
    return ring.union(markers)


def bearing(z):
    return tube(BEARING_OD, BEARING_ID, BEARING_H, z)


def motor_on_axis(z):
    body = cyl(MOTOR_OD, MOTOR_H, z)
    # rear shaft stub for magnet
    rear = cyl(3.0, 6.0, z - 6.0)
    front = cyl(INNER_SHAFT_D, 8.0, z + MOTOR_H)
    return body.union(rear).union(front)


def stepper_off_axis(x, y, z):
    body = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(x, y)
        .circle(STEPPER_BODY / 2)
        .extrude(19)
    )
    shaft = (
        cq.Workplane("XY")
        .workplane(offset=z + 19)
        .center(x, y)
        .circle(2.5)
        .extrude(8)
    )
    return body.union(shaft)


def pulley(x, y, z, od=PULLEY_OD):
    return (
        cq.Workplane("XY")
        .workplane(offset=z)
        .center(x, y)
        .circle(od / 2)
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
    plate = cyl(BASE_OD - 10, PLATE_TH, Z_PLATE)
    # solid minute shaft from rear magnet through dial
    minute_shaft = cyl(INNER_SHAFT_D, SHAFT_LEN, Z_MAG)
    # thin hollow hour tube — stops at dial front for hand
    hour_tube = tube(HOUR_TUBE_OD, HOUR_TUBE_ID, Z_HOUR_HAND - 10, 10)
    b1 = bearing(Z_BEARING1)
    b2 = bearing(Z_BEARING2)
    # Mercotac 205 capsule on FRONT shaft end (rotor collar + stator shell)
    slip_rotor = tube(SLIP_OD - 2, INNER_SHAFT_D + 0.2, SLIP_H - 2, Z_SLIP + 1)
    slip_stator = tube(SLIP_OD + 4, SLIP_OD - 1.5, SLIP_H, Z_SLIP)
    # AS5600 magnet + board at REAR
    mag = cyl(MAGNET_D, MAGNET_H, Z_MAG)
    enc = (
        cq.Workplane("XY")
        .workplane(offset=Z_ENC)
        .center(0, 0)
        .rect(ENC_BOARD, ENC_BOARD)
        .extrude(1.2)
    )
    # cut shaft clearance in enc board visually as ring around
    motor = motor_on_axis(Z_MOTOR)
    # off-axis hour stepper + belt to hour tube pulley
    step = stepper_off_axis(STEPPER_OFFSET, 0, -BASE_H + 2)
    p_step = pulley(STEPPER_OFFSET, 0, -BASE_H + 22)
    p_hour = pulley(0, 0, -BASE_H + 22, od=PULLEY_OD + 4)
    belt = belt_approx(STEPPER_OFFSET, 0, 0, 0, -BASE_H + 24)
    encl = tube(BASE_OD - 4, BASE_OD - 4 - 2 * ENCL_TH, ENCL_H, PLATE_TH)
    dial = dial_face(Z_DIAL)
    # annotate gap as thin spacer ring (visualization of LOCKED 5 mm)
    gap_vis = tube(HUB_R * 2 + 8, HUB_R * 2 + 4, AXIAL_GAP_BAR_TO_DIAL, Z_BAR + ARM_TH + LED_H)
    return (
        base.union(plate)
        .union(minute_shaft)
        .union(hour_tube)
        .union(b1)
        .union(b2)
        .union(slip_rotor)
        .union(slip_stator)
        .union(mag)
        .union(enc)
        .union(motor)
        .union(step)
        .union(p_step)
        .union(p_hour)
        .union(belt)
        .union(encl)
        .union(dial)
        .union(gap_vis)
    )


def build_pose(minute_deg, hour_deg):
    common = build_common()
    m = minute_hand(MINUTE_LEN, Z_BAR, minute_deg)
    h = hour_hand_only(HOUR_LEN, Z_HOUR_HAND, hour_deg)
    return common.union(m).union(h)


assy_clock = build_pose(MINUTE_CLOCK_DEG, HOUR_CLOCK_DEG)
assy_pov = build_pose(POV_MINUTE_DEG, POV_HOUR_DEG)
assy = assy_clock

# Exploded
exploded = (
    cyl(BASE_OD, BASE_H, -BASE_H)
    .union(cyl(BASE_OD - 10, PLATE_TH, 0))
    .union(dial_face(Z_DIAL).translate((0, 0, 20)))
    .union(minute_hand(MINUTE_LEN, Z_BAR, MINUTE_CLOCK_DEG).translate((0, 0, 35)))
    .union(hour_hand_only(HOUR_LEN, Z_HOUR_HAND, HOUR_CLOCK_DEG).translate((0, 0, 45)))
    .union(motor_on_axis(Z_MOTOR).translate((0, 0, -15)))
    .union(stepper_off_axis(STEPPER_OFFSET, 0, -BASE_H + 2).translate((30, 0, -10)))
    .union(tube(SLIP_OD + 4, SLIP_OD - 1.5, SLIP_H, Z_SLIP).translate((40, 0, 0)))
    .union(cyl(MAGNET_D, MAGNET_H, Z_MAG).translate((0, 0, -25)))
)

half = cq.Workplane("XY").box(
    BASE_OD * 1.2, BASE_OD * 1.2, 220, centered=(True, False, True)
)
section = assy.intersect(half.translate((0, -BASE_OD * 0.6, 20)))

exporters.export(assy, str(CAD / "pov_clock_assembly.step"))
exporters.export(assy, str(CAD / "pov_clock_assembly.stl"))
exporters.export(assy_clock, str(CAD / "pov_clock_clock_mode.stl"))
exporters.export(assy_pov, str(CAD / "pov_clock_pov_mode.stl"))
exporters.export(exploded, str(CAD / "pov_clock_exploded.stl"))
exporters.export(section, str(CAD / "pov_clock_section.stl"))

# Stack note file next to CAD
(CAD / "STACK_UP_NOTES.txt").write_text(
    f"""Clockor hybrid CAD v0.4 (Round 2)
Z_MAG={Z_MAG} AS5600 magnet rear
Z_MOTOR={Z_MOTOR} Furitek 2204
Z_SLIP={Z_SLIP} Mercotac 205 front
Z_BAR={Z_BAR} POV bar
Z_DIAL={Z_DIAL} clear acrylic (gap from bar top = {AXIAL_GAP_BAR_TO_DIAL} mm LOCKED incl. {HUB_RUNOUT_BUDGET} mm runout budget)
Z_HOUR_HAND={Z_HOUR_HAND} hour hand only in front of dial
Hour drive: off-axis stepper @ x={STEPPER_OFFSET} + belt to hollow tube OD={HOUR_TUBE_OD}
See docs/stack-up.md
"""
)

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
export_svg(assy_clock, "clock_front.svg", (0, 0, 1))
export_svg(assy_pov, "pov_iso.svg", (1.2, -1.5, 1.0))
export_svg(assy_pov, "pov_front.svg", (0, 0, 1))
export_svg(exploded, "exploded.svg", (1.2, -1.5, 1.0))
export_svg(section, "section.svg", (0.2, -1.0, 0.15))
export_svg(assy_clock, "front.svg", (0, -1, 0))
print("CAD v0.4 OK — hybrid Round 2 stack-up")
print(f"LOCKED axial gap bar→dial = {AXIAL_GAP_BAR_TO_DIAL} mm (Z_DIAL={Z_DIAL}, Z_BAR={Z_BAR})")
for p in sorted(CAD.glob("pov_*")) + sorted(CAD.glob("STACK*")):
    print(p.name, p.stat().st_size)
