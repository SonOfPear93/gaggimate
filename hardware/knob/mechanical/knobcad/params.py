"""All dimensions in mm. Change values here, then run build.py.

Frames
------
* Global / case frame: z = 0 is the TOP (front) face of board A, +z points at the
  user (out of the screen). The back case's housing-edge groove is on the +y side,
  so when the unit sits on the Gaggia, world "up" is roughly -y and the screen
  faces forward and ~23 deg upward (same as the stock GaggiMate display).
* Board frame: the frame the PCB generators use (math angles, CCW seen from the
  front, alignment holes of board A on the X axis). The whole internal stack
  (boards A/B/C, motor, MountBase, knob, screen platform, front case) is built in
  the board frame and rotated by STACK_ROT into the case frame. -90 puts the ESP32
  antenna of board B at the side (+x) instead of next to the machine's sheet metal
  (+y), and keeps board B's controller connector J2 clear of both grooves.
"""
import math

# ------------------------------------------------------------------ general
STACK_ROT = -90.0           # board frame -> case frame rotation about z (deg)
CLR = 0.25                  # generic FDM clearance (radial) for slip fits
GAP_ROT = 0.6               # min gap between rotating and stationary parts

# ------------------------------------------------------------------ case
CASE_OD = 78.6              # stock GaggiMate is Ø77.8; +0.8 mm gives a 1.55 mm wall at board A
R_CASE = CASE_OD / 2

# ------------------------------------------------------------------ board A (knob-base)
A_R = 37.5                  # Ø75
A_T = 1.2
A_M2_R, A_M2_ANG = 29.8, (0, 90, 180, 270)
A_PIN_R, A_PIN_ANG, A_PIN_HOLE = 35.0, (0, 180), 2.2
A_SLOT = dict(r=33.5, ang=225.0, w=3.0, l=7.0)
A_MOTOR_HOLE_R, A_MOTOR_HOLE_ANG = 10.25, (60, 180, 300)   # M1.6, from knob-base gen_pcb.py
A_WIRE_HOLE = dict(r=10.0, ang=225.0, d=3.0)              # SmartKnob centre-island wire hole
A_MOTOR_SLOT = dict(x0=7.0, x1=10.5, w=7.0)               # island slot at 0 deg (motor wires)

# ------------------------------------------------------------------ board B (knob-main)
B_R = 37.0                  # Ø74
B_T = 1.6
AB_GAP = 8.0                # board A bottom face -> board B top face
B_TOP = -A_T - AB_GAP       # -9.2
B_BOT = B_TOP - B_T         # -10.8
B_HOLE_R, B_HOLE_ANG = 33.0, (22.5, 112.5, 202.5, 292.5)   # coordinator update 2026-11-07
B_BOTTOM_COMP = 3.0         # doc: max 3 mm on the bottom except connectors
# connector positions taken from knob-main.kicad_pcb (work in progress, re-check!)
B_USB = dict(x=-33.2, y=0.0, axis_deg=180.0, h=3.26)      # HRO TYPE-C-31-M-12 on top side (final knob-main J1, mating face at the Ø74 edge)
B_XH = dict(x=16.0, y=-10.3, w=20.0, d=8.5)               # J2 B4B-XH-A vertical, bottom side

# ------------------------------------------------------------------ board C (knob-screen)
C_R = 23.0                  # Ø46
C_T = 1.6
C_HOLE_R, C_HOLE_ANG = 19.5, (90, 210, 330)               # 3x M2 (knob-screen.kicad_pcb)
C_PADS_R = 5.5              # ring of 13 wire pads on the back

# ------------------------------------------------------------------ panel (Waveshare 1.75" CO5300)
GLASS_R = 48.96 / 2
GLASS_T = 1.10
PANEL_T = 2.05              # glass + OLED module
MODULE_R = 23.0
PANEL_BACK_EXTRA = 1.35     # folded FPC + driver IC behind the module (STEP: y -0.63)
PANEL_TO_C = 5.70           # front face -> board C front face, same as Waveshare's carrier
FPC_ANG = (90.0, 270.0)     # board-frame angles where the FPC folds round the module edge
FPC_NOTCH_W = 14.0
TAPE_T = 0.2                # double-sided tape ring between rim and glass

# ------------------------------------------------------------------ motor (SparkFun ROB-20441) + SmartKnob stack
MB_TOP = 6.0                # MountBase top = motor base
MAGNET = dict(r_o=6.0, r_i=3.0, z0=3.75, z1=6.0)          # assumed ring magnet
STATOR_R = 14.0             # assumed, base flange of the stator
ROTOR_R, ROTOR_Z0, ROTOR_Z1 = 16.0, 9.75, 18.75
SHAFT_RI, SHAFT_RO, SHAFT_TOP = 2.95, 4.0, 19.6           # 5.9 mm bore; OD/top assumed
SPACER_TOP = 20.25          # SmartKnob RotorSpacer top face
SPACER_LOBE_R = 22.5        # its 5 crush lobes
SPACER_LOBE_ANG0 = 180.0    # spacer placed rotated 180 deg (lobes at 180+72k in board frame)

# ------------------------------------------------------------------ MountBase (SmartKnob, modified)
MB = dict(
    r=15.0, flange=False, flange_r=21.5, flange_z=(3.0, 4.5),
    magnet_r=6.25, magnet_z0=3.5,
    tube_ro=2.75, tube_ri=1.7, tube_z0=2.0,
    pocket=(7.0, 8.5, 2.0),            # MT6701 pocket (x, y, depth)
    chan_w=4.0, chan_h=2.7, chan_ang=225.0,
    mslot=(9.0, 13.0, 8.0),            # motor-wire slot r0, r1, width at 0 deg
    hole_d=1.8,
)

# ------------------------------------------------------------------ screen platform
PLAT_Z0 = SPACER_TOP + GAP_ROT          # 20.85 underside
PLAT_FLOOR_T = 1.6
PLAT_POCKET = 2.5                       # room under board C for the 13 solder joints
C_BACK = PLAT_Z0 + PLAT_FLOOR_T + PLAT_POCKET   # 24.95
C_FRONT = C_BACK + C_T                  # 26.55
F = C_FRONT + PANEL_TO_C                # panel / knob front face, 32.25
PLAT_RIM_RI = C_R + 0.2
PLAT_LEDGE_RI = 17.5
PLAT_BOSS = dict(r=3.9, h=0.8)          # collar round the tube socket
PLAT_SOCKET_R = 2.80                    # on the 2.75 tube, glue
MB_TUBE_TOP = PLAT_Z0 + PLAT_FLOOR_T + PLAT_BOSS['h'] - 0.3

# ------------------------------------------------------------------ knob ring
KNOB_R = 33.0                           # Ø66
KNOB_BORE_R = GLASS_R + 0.5             # 0.5 mm radial gap round the glass
KNOB_HUB_RI = 21.0                      # bore over the RotorSpacer (lobes key into notches)
KNOB_HUB_RO = 25.0
KNOB_HUB_Z0 = 14.25                     # 6 mm engagement on the spacer
KNOB_CHAMF_Z = SPACER_TOP + 0.1         # bore starts opening out above the spacer
KNOB_WALL = 2.0                         # outer skirt
KNOB_LIP_T = 2.0                        # front lip (annulus round the glass)
KNOB_INNER_WALL = 1.6
KNOB_SKIRT_Z0 = 16.0                    # bottom of the outer wall (hidden in the case well)
KNOB_NOTCH_W = 1.7
KNURL_N, KNURL_R, KNURL_DEPTH = 60, 0.9, 0.55

# ------------------------------------------------------------------ front case
FC_WELL_R = KNOB_R + GAP_ROT            # 33.6
Z_CF = 19.0                             # front face of the case (knob protrudes F - Z_CF)
Z_J = 8.0                               # seam between front and back case
DECK_Z0, DECK_Z1, DECK_RI = 3.0, 5.0, 26.5
SPIGOT_RI = 35.6
BACK_BORE_A = A_R + CLR                 # 37.75 (board A must pass)
SPIGOT_RO = BACK_BORE_A - 0.2           # 37.55
M2_INSERT = dict(d=3.2, depth=4.0)      # M2 heat-set insert (e.g. M2x3 OD3.5)
M3_INSERT = dict(d=4.0, depth=5.7)
FC_BOSS_D = 6.0
PIN_D, PIN_LEN = 2.0, 1.4               # below board A top
RADIAL_SCREW_ANG = (60.0, 180.0, 300.0) # case frame
RADIAL_SCREW_Z = 5.4
CHAMFER_FRONT = 0.8
WIRE_CHAN_W = 8.0                       # deck-underside channel for the 16 wires

# ------------------------------------------------------------------ back case
BACK_BORE_B = B_R + CLR                 # 37.25
Z_FLOOR = B_BOT - B_BOTTOM_COMP - 1.2   # -15.0
B_POST_D = 6.0
# stock GaggiMate back-block YZ profiles (x = 0 section of case_back_*.stl, stock z).
# Only the part below the stock z = -18.2 line is used (the chamfers start there).
STOCK_PROFILES = {
    'classic': [(38.9, -18.2), (32.9, -32.33), (19.1, -26.46), (18.55, -27.75),
                (25.45, -30.68), (24.76, -32.33), (-30.74, -32.33), (-38.9, -18.2)],
    'classic_pro': [(38.9, -18.2), (33.65, -30.56), (28.75, -30.56), (5.29, -20.6),
                    (4.74, -21.89), (11.65, -24.82), (9.21, -30.56), (-31.76, -30.56),
                    (-38.9, -18.2)],
}
STOCK_TOP = -18.2
BLOCK_DZ = Z_FLOOR - STOCK_TOP          # shift stock -> case frame (+3.2)
# clamp: M3 thumbscrew from the bottom face, tip on the sheet opposite the tooth
CLAMP = {
    'classic':     dict(E=(36.42, -24.05), Q=(22.78, -28.02), screw='M3x20'),
    'classic_pro': dict(E=(36.42, -24.05), Q=(16.33, -25.29), screw='M3x25'),
}
CLAMP_X = 0.0
USB_CUT = dict(w=13.0, h=7.0)
CABLE_CUT_EXTRA = 0.0


def polar(r, deg):
    a = math.radians(deg)
    return (r * math.cos(a), r * math.sin(a))


def to_case_deg(board_deg):
    return board_deg + STACK_ROT


def to_board_deg(case_deg):
    return case_deg - STACK_ROT
