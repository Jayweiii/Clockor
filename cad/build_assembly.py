#!/usr/bin/env python3
"""Hybrid Clockor mechanical assembly (CadQuery) — v0.6 coaxial redesign.

Minute = spinning POV bar on a HOLLOW minute tube driven by a hollow-shaft
         gimbal BLDC (2804 class, ~100 KV on a 24 V bus).
Hour   = Ø3 mm shaft running INSIDE the minute tube (two MR63 bearings), out
         through the bar hub and a Ø5 hole in the dial. Driven 1:1 by a
         28BYJ-48 coaxial at the very rear through a shaft coupler.
         Nothing but the hour hand sits in front of the dial — v0.5 put the
         stepper, pulleys and belt on the dial face, over the POV image.
Encoder = MagAlpha MA730 side-shaft beside a ring magnet on the minute tube
          (the rear shaft end is taken by the hour shaft, so AS5600 end-of-shaft
          sensing is no longer possible).
Slip   = SenRing G012 through-bore brush ring on the minute tube (collar).
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
BASE_H = 72.0                # deeper base: coaxial stepper + coupler + encoder at rear
PLATE_TH = 4.0
ENCL_H = 60.0
ENCL_TH = 2.5
MINUTE_LEN = 80.0             # per side (bar PCB is 160 mm overall); v0.5 drew 150 per side = 300 mm
HOUR_LEN = 60.0               # must stay inside the dial markers (v0.5: 110 > dial radius)
ARM_W = 10.0
ARM_TH = 1.6
HUB_R = 14.0
MINUTE_TUBE_OD = 6.0         # hollow minute shaft ESTIMATE (or motor hollow shaft + extension)
MINUTE_TUBE_ID = 4.0
HOUR_SHAFT_D = 3.0           # inner hour shaft, runs in 2× MR63 (3×6×2.5) inside the tube
BEARING_OD = 16.0
BEARING_ID = 5.0
BEARING_H = 5.0
MOTOR_OD = 34.0              # hollow-shaft gimbal BLDC 2804 class ESTIMATE
MOTOR_H = 14.0
STEPPER_BODY = 28.0          # 28BYJ-48: Ø28 × 19 body, shaft offset 8 mm from body centre
STEPPER_SHAFT_OFFSET = 8.0
COUPLER_D = 10.0
# SenRing G012 envelope ESTIMATE (through-bore brush capsule)
SLIP_OD = 35.0
SLIP_ID = 12.7
SLIP_H = 22.0
RING_MAG_OD = 12.0           # diametric ring magnet on minute tube (side-shaft MA730)
RING_MAG_H = 3.0
ENC_BOARD = 14.0
DIAL_ID = 5.0                # clearance hole for the Ø3 hour shaft only
DIAL_OD = BASE_OD - 18.0
DIAL_TH = 2.0
MARKER_INNER = DIAL_OD / 2 - 14.0
MARKER_OUTER = DIAL_OD / 2 - 2.0
LED_SIZE = 2.0
LED_H = 0.9
N_LED_MIN = 36
AXIAL_GAP_BAR_TO_DIAL = 5.0  # mm LOCKED
HUB_RUNOUT_BUDGET = 1.0
HOUR_HOME_MAG_D = 2.0
HOUR_HOME_MAG_H = 1.0

# Z stations (rear negative → front positive)
Z_MOTOR = -MOTOR_H
Z_MAG = Z_MOTOR - 8.0                       # ring magnet on minute tube, behind motor
Z_TUBE0 = Z_MAG - 1.0                       # minute tube rear end
Z_COUPLER = Z_TUBE0 - 12.0                  # hour coupler (+ hour-home magnet)
Z_STEPPER_SHAFT_TIP = Z_COUPLER + 4.0
Z_STEPPER = Z_STEPPER_SHAFT_TIP - 10.0 - 19.0   # body rear face
Z_PLATE = 0.0
Z_BEARING1 = 6.0
Z_BEARING2 = 22.0
Z_SLIP = 28.0
Z_HUB = Z_SLIP + SLIP_H + 2.0
Z_BAR = Z_HUB
Z_DIAL = Z_BAR + ARM_TH + LED_H + AXIAL_GAP_BAR_TO_DIAL
Z_TUBE1 = Z_HUB + ARM_TH + 1.5              # minute tube front end (well behind dial)
Z_HOUR_HAND = Z_DIAL + DIAL_TH + 1.5        # only the hand is in front of the dial
Z_HOUR_SHAFT1 = Z_HOUR_HAND + 2.5


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
    blank = (
        cq.Workplane("XY")
        .workplane(offset=z)
        .moveTo(0, 0)
        .circle(5)
        .moveTo(length / 2, 0)
        .rect(length, 6)
        .extrude(1.2)
        .rotate((0, 0, 0), (0, 0, 1), clock_to_cq(clock_deg))
    )
    return blank


def dial_face(z):
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


def bearing(z, od=BEARING_OD, id_=BEARING_ID, h=BEARING_H):
    return tube(od, id_, h, z)


def motor_on_axis(z):
    """Hollow-shaft gimbal motor: annular body, bore passes the minute tube."""
    return tube(MOTOR_OD, MINUTE_TUBE_OD + 1.0, MOTOR_H, z)


def stepper_coaxial(z):
    """28BYJ-48 at the rear with its OUTPUT SHAFT on the clock axis (body offset)."""
    body = cyl(STEPPER_BODY, 19, z).translate((0, -STEPPER_SHAFT_OFFSET, 0))
    shaft = cyl(5.0, 10.0, z + 19)
    return body.union(shaft)


def build_common():
    base = tube(BASE_OD, BASE_OD - 2 * ENCL_TH, BASE_H, -BASE_H).union(cyl(BASE_OD, 3.0, -BASE_H))
    plate = cyl(BASE_OD - 10, PLATE_TH, Z_PLATE)
    minute_tube = tube(MINUTE_TUBE_OD, MINUTE_TUBE_ID, Z_TUBE1 - Z_TUBE0, Z_TUBE0)
    hour_shaft = cyl(HOUR_SHAFT_D, Z_HOUR_SHAFT1 - Z_COUPLER, Z_COUPLER)
    b1 = bearing(Z_BEARING1, id_=MINUTE_TUBE_OD)
    b2 = bearing(Z_BEARING2, id_=MINUTE_TUBE_OD)
    # SenRing G012-class through-bore brush ring on the minute tube (collar adapter)
    slip_rotor = tube(SLIP_ID, MINUTE_TUBE_OD, SLIP_H - 4, Z_SLIP + 2)
    slip_stator = tube(SLIP_OD, SLIP_ID + 0.5, SLIP_H, Z_SLIP)
    ring_mag = tube(RING_MAG_OD, MINUTE_TUBE_OD, RING_MAG_H, Z_MAG)
    enc = (  # MA730 satellite beside the ring magnet (side-shaft)
        cq.Workplane("XY").workplane(offset=Z_MAG - 3.0)
        .center(RING_MAG_OD / 2 + 2.5 + ENC_BOARD / 2, 0)
        .rect(ENC_BOARD, ENC_BOARD).extrude(1.2)
    )
    motor = motor_on_axis(Z_MOTOR)
    coupler = cyl(COUPLER_D, 8.0, Z_COUPLER)
    hour_home_mag = cyl(HOUR_HOME_MAG_D, HOUR_HOME_MAG_H, Z_COUPLER + 3.5).translate((COUPLER_D / 2, 0, 0))
    step = stepper_coaxial(Z_STEPPER)
    encl = tube(BASE_OD - 4, BASE_OD - 4 - 2 * ENCL_TH, ENCL_H, PLATE_TH)
    dial = dial_face(Z_DIAL)
    gap_vis = tube(HUB_R * 2 + 8, HUB_R * 2 + 4, AXIAL_GAP_BAR_TO_DIAL, Z_BAR + ARM_TH + LED_H)
    return (
        base.union(plate)
        .union(minute_tube)
        .union(hour_shaft)
        .union(b1)
        .union(b2)
        .union(slip_rotor)
        .union(slip_stator)
        .union(ring_mag)
        .union(enc)
        .union(motor)
        .union(coupler)
        .union(hour_home_mag)
        .union(step)
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

exploded = (
    cyl(BASE_OD, 3.0, -BASE_H)
    .union(cyl(BASE_OD - 10, PLATE_TH, 0))
    .union(dial_face(Z_DIAL).translate((0, 0, 30)))
    .union(minute_hand(MINUTE_LEN, Z_BAR, MINUTE_CLOCK_DEG).translate((0, 0, 15)))
    .union(hour_hand_only(HOUR_LEN, Z_HOUR_HAND, HOUR_CLOCK_DEG).translate((0, 0, 45)))
    .union(motor_on_axis(Z_MOTOR))
    .union(tube(MINUTE_TUBE_OD, MINUTE_TUBE_ID, Z_TUBE1 - Z_TUBE0, Z_TUBE0).translate((0, 0, 8)))
    .union(cyl(HOUR_SHAFT_D, Z_HOUR_SHAFT1 - Z_COUPLER, Z_COUPLER).translate((0, 0, 22)))
    .union(tube(SLIP_OD, SLIP_ID + 0.5, SLIP_H, Z_SLIP).translate((50, 0, 0)))
    .union(tube(RING_MAG_OD, MINUTE_TUBE_OD, RING_MAG_H, Z_MAG).translate((0, 0, -8)))
    .union(cyl(COUPLER_D, 8.0, Z_COUPLER).translate((0, 0, -14)))
    .union(stepper_coaxial(Z_STEPPER).translate((0, 0, -26)))
)

half = cq.Workplane("XY").box(
    BASE_OD * 1.2, BASE_OD * 1.2, 240, centered=(True, False, True)
)
section = assy.intersect(half.translate((0, -BASE_OD * 0.6, 30)))

exporters.export(assy, str(CAD / "pov_clock_assembly.step"))
exporters.export(assy, str(CAD / "pov_clock_assembly.stl"))
exporters.export(assy_clock, str(CAD / "pov_clock_clock_mode.stl"))
exporters.export(assy_pov, str(CAD / "pov_clock_pov_mode.stl"))
exporters.export(exploded, str(CAD / "pov_clock_exploded.stl"))
exporters.export(section, str(CAD / "pov_clock_section.stl"))

(CAD / "STACK_UP_NOTES.txt").write_text(
    f"""Clockor hybrid CAD v0.6 (coaxial hour shaft)
Z_STEPPER={Z_STEPPER} 28BYJ-48 body rear face, output shaft on axis
Z_COUPLER={Z_COUPLER} hour coupler + hour-home magnet (hall on J9)
Z_MAG={Z_MAG} ring magnet on minute tube, MA730 side-shaft (J10)
Z_MOTOR={Z_MOTOR} hollow-shaft gimbal BLDC 2804 class
Z_SLIP={Z_SLIP} SenRing G012 through-bore brush ring on minute tube
Z_BAR={Z_BAR} POV bar (hub on minute tube)
Z_DIAL={Z_DIAL} clear acrylic, centre hole D={DIAL_ID} (gap from bar top = {AXIAL_GAP_BAR_TO_DIAL} mm LOCKED incl. {HUB_RUNOUT_BUDGET} mm runout budget)
Z_HOUR_HAND={Z_HOUR_HAND} hour hand — the ONLY part in front of the dial
Hour shaft D={HOUR_SHAFT_D} inside minute tube {MINUTE_TUBE_OD}/{MINUTE_TUBE_ID}, 1:1 direct coupling (no belt)
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
export_svg(section, "section.svg", (0.0, 1.0, 0.0))
export_svg(assy_clock, "front.svg", (0, -1, 0))
print("CAD v0.6 OK — coaxial hour shaft, hollow gimbal BLDC, SenRing slip")
print(f"LOCKED axial gap bar→dial = {AXIAL_GAP_BAR_TO_DIAL} mm (Z_DIAL={Z_DIAL}, Z_BAR={Z_BAR})")
print(f"Hour hand Z={Z_HOUR_HAND}; nothing else in front of dial Z={Z_DIAL}")
for p in sorted(CAD.glob("pov_*")) + sorted(CAD.glob("STACK*")):
    print(p.name, p.stat().st_size)
