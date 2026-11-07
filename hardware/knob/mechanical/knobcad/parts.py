"""Parametric parts (build123d). Every builder returns a Part in its *assembly*
position. Internal-stack parts are built in the board frame; use `to_case()` to
rotate them into the case frame (see params.py)."""
import math

from build123d import (Align, Axis, Box, Cylinder, Part, Plane, Polygon, Pos, Rot,
                       RectangleRounded, extrude, revolve)

from .params import *  # noqa: F401,F403
from . import params as P

MIN = (Align.CENTER, Align.CENTER, Align.MIN)


# ------------------------------------------------------------------ helpers
def revolve_rz(pts):
    """Revolve a closed (r, z) polygon about the z axis."""
    return revolve(Plane.XZ * Polygon(*pts, align=None), Axis.Z, 360)


def cyl(r, z0, z1, x=0.0, y=0.0):
    return Pos(x, y, z0) * Cylinder(r, z1 - z0, align=MIN)


def ring(ri, ro, z0, z1):
    return cyl(ro, z0, z1) - cyl(ri, z0 - 0.01, z1 + 0.01)


def radial_box(r0, r1, w, z0, z1, ang):
    """Box spanning radius r0..r1, width w (tangential), at angle ang (deg)."""
    b = Pos((r0 + r1) / 2, 0, z0) * Box(r1 - r0, w, z1 - z0, align=MIN)
    return Rot(0, 0, ang) * b


def at_polar(obj, r, ang):
    x, y = polar(r, ang)
    return Pos(x, y, 0) * obj


def rod(p0, p1, r):
    """Cylinder from point p0 to p1 (3-tuples)."""
    dx, dy, dz = (p1[i] - p0[i] for i in range(3))
    L = math.sqrt(dx * dx + dy * dy + dz * dz)
    # rotate +z onto (dx,dy,dz): first about y (tilt), then about z (azimuth)
    tilt = math.degrees(math.acos(dz / L))
    az = math.degrees(math.atan2(dy, dx))
    c = Cylinder(r, L, align=MIN)
    return Pos(*p0) * Rot(0, 0, az) * Rot(0, tilt, 0) * c


def to_case(part):
    return Rot(0, 0, P.STACK_ROT) * part


def union_all(items):
    out = items[0]
    for it in items[1:]:
        out = out + it
    return out


# ------------------------------------------------------------------ knob ring
def knob():
    c = P.CHAMFER_FRONT
    rb, R = P.KNOB_BORE_R, P.KNOB_R
    t_lip, t_in = P.KNOB_LIP_T, P.KNOB_INNER_WALL
    r_in = rb + t_in                                    # inner wall outer face
    z_c1 = P.KNOB_CHAMF_Z + (rb - P.KNOB_HUB_RI)        # top of the 45 deg bore chamfer
    pts = [
        (rb + 0.3, P.F), (R - c, P.F), (R, P.F - c),
        (R, P.KNOB_SKIRT_Z0), (R - P.KNOB_WALL, P.KNOB_SKIRT_Z0),      # outer skirt
        (R - P.KNOB_WALL, P.F - t_lip), (r_in, P.F - t_lip),           # under the front lip
        (r_in, z_c1), (P.KNOB_HUB_RO, z_c1 - (r_in - P.KNOB_HUB_RO)),  # 45 deg down to the hub
        (P.KNOB_HUB_RO, P.KNOB_HUB_Z0), (P.KNOB_HUB_RI, P.KNOB_HUB_Z0),
        (P.KNOB_HUB_RI, P.KNOB_CHAMF_Z),
        (rb, z_c1),                                                    # 45 deg, clears platform
        (rb, P.F - 0.3),
    ]
    k = revolve_rz(pts)
    # notches for the 5 RotorSpacer lobes (positive key + press fit on lobe tips)
    notches = [radial_box(P.KNOB_HUB_RI - 0.5, P.SPACER_LOBE_R, P.KNOB_NOTCH_W,
                          P.KNOB_HUB_Z0 - 1, P.KNOB_CHAMF_Z + 0.01,
                          P.SPACER_LOBE_ANG0 + 72 * i) for i in range(5)]
    k = k - union_all(notches)
    # straight knurl (vertical flutes print cleanly in any orientation)
    rc = P.KNOB_R + P.KNURL_R - P.KNURL_DEPTH
    flutes = [at_polar(cyl(P.KNURL_R, P.KNOB_SKIRT_Z0 - 1, P.F - 1.2), rc, 360 / P.KNURL_N * i)
              for i in range(P.KNURL_N)]
    k = k - union_all(flutes)
    return k


# ------------------------------------------------------------------ screen platform
def screen_platform():
    z0 = P.PLAT_Z0
    zf = z0 + P.PLAT_FLOOR_T
    zc = P.C_BACK
    ztop = P.F - P.GLASS_T - P.TAPE_T
    # outer flank parallel to the knob's 45 deg bore chamfer, GAP_ROT away
    # (horizontal offset GAP_ROT*sqrt2 => GAP_ROT measured square to the 45 deg faces)
    r_bot = P.KNOB_HUB_RI + (z0 - P.KNOB_CHAMF_Z) - P.GAP_ROT * math.sqrt(2)
    r_rim = P.KNOB_BORE_R - P.GAP_ROT
    pts = [
        (P.PLAT_SOCKET_R, z0), (r_bot, z0), (r_rim, z0 + (r_rim - r_bot)),
        (r_rim, ztop), (P.PLAT_RIM_RI, ztop), (P.PLAT_RIM_RI, zc),
        (P.PLAT_LEDGE_RI, zc), (P.PLAT_LEDGE_RI, zf),
        (P.PLAT_BOSS['r'], zf), (P.PLAT_BOSS['r'], zf + P.PLAT_BOSS['h']),
        (P.PLAT_SOCKET_R, zf + P.PLAT_BOSS['h']),
    ]
    p = revolve_rz(pts)
    # notches in the rim where the panel FPCs wrap round the module edge
    for a in P.FPC_ANG:
        p = p - radial_box(P.PLAT_RIM_RI - 2.0, r_rim + 1, P.FPC_NOTCH_W, P.C_FRONT, ztop + 1, a)
    # M2 heat-set inserts for board C's three holes
    for a in P.C_HOLE_ANG:
        p = p - at_polar(cyl(P.M2_INSERT['d'] / 2, zc - 3.5, zc + 0.01), P.C_HOLE_R, a)
    return p


# ------------------------------------------------------------------ MountBase
def mountbase():
    m = P.MB
    b = cyl(m['r'], 0, P.MB_TOP)
    if m['flange']:   # SmartKnob's light-shield flange; no function here and a 6.5 mm overhang
        b = b + ring(m['r'] - 0.01, m['flange_r'], *m['flange_z'])
    b = b - cyl(m['magnet_r'], m['magnet_z0'], P.MB_TOP + 0.01)
    b = b + ring(m['tube_ri'], m['tube_ro'], m['tube_z0'], P.MB_TUBE_TOP)
    b = b - cyl(m['tube_ri'], -0.01, P.MB_TUBE_TOP + 0.01)
    px, py, pd = m['pocket']
    b = b - Pos(0, 0, -0.01) * Box(px, py, pd + 0.01, align=MIN)
    # wire channel: SmartKnob's 45 deg channel (225 deg in board frame) extended
    # through the outer wall so the bundle can run over board A to its slot
    b = b - radial_box(0, m['flange_r'] + 1, m['chan_w'], -0.01, m['chan_h'], m['chan_ang'])
    r0, r1, w = m['mslot']
    b = b - radial_box(r0, r1, w, -0.01, P.MB_TOP + 0.01, 0)
    for a in P.A_MOTOR_HOLE_ANG:
        b = b - at_polar(cyl(m['hole_d'] / 2, -0.01, P.MB_TOP + 0.01), P.A_MOTOR_HOLE_R, a)
    return b


# ------------------------------------------------------------------ front case
def front_case():
    c = P.CHAMFER_FRONT
    pts = [
        (P.DECK_RI, P.DECK_Z0), (P.SPIGOT_RI, P.DECK_Z0), (P.SPIGOT_RI, 0.0),
        (P.SPIGOT_RO, 0.0), (P.SPIGOT_RO, P.Z_J), (P.R_CASE, P.Z_J),
        (P.R_CASE, P.Z_CF - c), (P.R_CASE - c, P.Z_CF),
        (P.FC_WELL_R + 0.5, P.Z_CF), (P.FC_WELL_R, P.Z_CF - 0.5),
        (P.FC_WELL_R, P.DECK_Z1 + (P.FC_WELL_R - P.DECK_RI)),           # 45 deg cone
        (P.DECK_RI, P.DECK_Z1),
    ]
    fc = revolve_rz(pts)
    adds, cuts = [], []
    # 4x M2 bosses that clamp board A's ring (insert from below, screw from behind A)
    for a in P.A_M2_ANG:
        adds.append(at_polar(cyl(P.FC_BOSS_D / 2, 0.0, P.DECK_Z0 + 0.5), P.A_M2_R, a))
        cuts.append(at_polar(cyl(P.M2_INSERT['d'] / 2, -0.01, P.M2_INSERT['depth']), P.A_M2_R, a))
    # 2x alignment pins through board A
    for a in P.A_PIN_ANG:
        adds.append(at_polar(cyl(2.0, 0.0, P.DECK_Z0 + 0.5), P.A_PIN_R, a))
        pin = cyl(P.PIN_D / 2, -P.PIN_LEN + 0.3, 0.01) + \
            Pos(0, 0, -P.PIN_LEN) * Cylinder(P.PIN_D / 2 - 0.3, 0.3, align=MIN)
        adds.append(at_polar(pin, P.A_PIN_R, a))
    # radial M2 inserts joining front case to back case
    for ca in P.RADIAL_SCREW_ANG:
        a = P.to_board_deg(ca)
        adds.append(radial_box(P.FC_WELL_R, P.SPIGOT_RO, 7.0, 2.5, P.Z_J, a))
        x0, y0 = polar(P.SPIGOT_RO + 0.01, a)
        x1, y1 = polar(P.SPIGOT_RO - 4.5, a)
        cuts.append(rod((x0, y0, P.RADIAL_SCREW_Z), (x1, y1, P.RADIAL_SCREW_Z), P.M2_INSERT['d'] / 2))
    fc = fc + union_all(adds)
    # wire channel: recess in the deck underside along the slot's ray (MountBase exit -> slot)
    cuts.append(radial_box(P.DECK_RI - 1, P.SPIGOT_RI + 0.01, P.WIRE_CHAN_W, -0.01, P.DECK_Z0 + 1.0,
                           P.A_SLOT['ang']))
    fc = fc - union_all(cuts)
    return fc


# ------------------------------------------------------------------ back case
def back_case(variant='classic'):
    R = P.R_CASE
    prof = [(y, z + P.BLOCK_DZ) for y, z in P.STOCK_PROFILES[variant]]
    z_back = min(z for _, z in prof)
    # extend both chamfers 2 mm above the floor so the profile overlaps the shell
    # (avoids tangent/coincident faces in the booleans)
    zt = P.Z_FLOOR + 2.0

    def ext(a, b):
        (y0, z0), (y1, z1) = a, b
        return (y0 + (zt - z0) * (y0 - y1) / (z0 - z1), zt)
    prof = [ext(prof[0], prof[1])] + prof[1:-1] + [ext(prof[-1], prof[-2])]
    block = extrude(Plane.YZ * Polygon(*prof, align=None), amount=R + 2, both=True)
    block = block & cyl(R, z_back - 1, P.Z_FLOOR + 1.0)
    shell = cyl(R, P.Z_FLOOR, P.Z_J)
    # small chamfer on the seam edge
    shell = shell - revolve_rz([(R - 0.4, P.Z_J + 0.01), (R + 0.01, P.Z_J + 0.01), (R + 0.01, P.Z_J - 0.41)])
    bc = shell + block
    zA = -P.A_T - 0.2
    bc = bc - cyl(P.BACK_BORE_A, zA, P.Z_J + 0.01)
    bc = bc - cyl(P.BACK_BORE_B, P.Z_FLOOR, zA + 0.01)
    adds, cuts = [], []
    # board B posts with M2 inserts
    for a in P.B_HOLE_ANG:
        ca = P.to_case_deg(a)
        adds.append(at_polar(cyl(P.B_POST_D / 2, P.Z_FLOOR - 0.01, P.B_BOT), P.B_HOLE_R, ca))
        cuts.append(at_polar(cyl(P.M2_INSERT['d'] / 2, P.B_BOT - P.M2_INSERT['depth'], P.B_BOT + 0.01),
                             P.B_HOLE_R, ca))
    # radial screw clearance holes (M2 button head)
    for ca in P.RADIAL_SCREW_ANG:
        x0, y0 = polar(R + 1, ca)
        x1, y1 = polar(P.BACK_BORE_A - 0.5, ca)
        cuts.append(rod((x0, y0, P.RADIAL_SCREW_Z), (x1, y1, P.RADIAL_SCREW_Z), 1.2))
    # USB-C opening (board B J1)
    ux, uy = P.B_USB['x'], P.B_USB['y']
    cx, cy = polar(math.hypot(ux, uy), math.degrees(math.atan2(uy, ux)) + P.STACK_ROT)
    axis = P.B_USB['axis_deg'] + P.STACK_ROT
    zc = P.B_TOP + P.B_USB['h'] / 2
    slot = extrude(Plane.XZ * RectangleRounded(P.USB_CUT['w'], P.USB_CUT['h'], 2.0), amount=15)
    # Plane.XZ extrudes towards -y; turn it so it points along `axis`
    slot = Pos(cx, cy, zc) * Rot(0, 0, axis + 90) * slot
    cuts.append(slot)
    # controller cable duct under J2 (JST-XH plugs in from below, cable exits the back face)
    hx, hy = P.B_XH['x'], P.B_XH['y']
    cxh, cyh = polar(math.hypot(hx, hy), math.degrees(math.atan2(hy, hx)) + P.STACK_ROT)
    duct = Box(P.B_XH['w'], P.B_XH['d'], P.Z_FLOOR - z_back + 2, align=MIN)
    duct = Pos(cxh, cyh, z_back - 1) * Rot(0, 0, P.STACK_ROT) * duct
    cuts.append(duct)
    # housing clamp: M3 heat-set insert + thumbscrew from the bottom face
    cl = P.CLAMP[variant]
    E = (P.CLAMP_X, cl['E'][0], cl['E'][1] + P.BLOCK_DZ)
    Q = (P.CLAMP_X, cl['Q'][0], cl['Q'][1] + P.BLOCK_DZ)
    L = math.dist(E, Q)
    d = tuple((Q[i] - E[i]) / L for i in range(3))
    pt = lambda s: tuple(E[i] + s * d[i] for i in range(3))  # noqa: E731
    cuts.append(rod(pt(-12), pt(1.0), 4.0))                              # spot face
    cuts.append(rod(pt(0.9), pt(1.0 + P.M3_INSERT['depth']), P.M3_INSERT['d'] / 2))
    cuts.append(rod(pt(0.9), pt(L + 2.5), 1.7))                          # M3 clearance to the groove
    bc = bc + union_all(adds)
    bc = bc - union_all(cuts)
    return bc


# ------------------------------------------------------------------ stand-ins (not printed)
def board_a():
    b = cyl(P.A_R, -P.A_T, 0.0)
    cuts = []
    for a in P.A_M2_ANG:
        cuts.append(at_polar(cyl(1.1, -2, 1), P.A_M2_R, a))
    for a in P.A_PIN_ANG:
        cuts.append(at_polar(cyl(P.A_PIN_HOLE / 2, -2, 1), P.A_PIN_R, a))
    for a in P.A_MOTOR_HOLE_ANG:
        cuts.append(at_polar(cyl(0.85, -2, 1), P.A_MOTOR_HOLE_R, a))
    s = P.A_SLOT
    cuts.append(Rot(0, 0, s['ang']) * Pos(s['r'], 0, -2) * Box(s['w'], s['l'], 3, align=MIN))
    w = P.A_WIRE_HOLE
    cuts.append(at_polar(cyl(w['d'] / 2, -2, 1), w['r'], w['ang']))
    ms = P.A_MOTOR_SLOT
    cuts.append(Pos((ms['x0'] + ms['x1']) / 2, 0, -2) * Box(ms['x1'] - ms['x0'], ms['w'], 3, align=MIN))
    b = b - union_all(cuts)
    b = b + Box(4.9, 6.0, 1.5, align=MIN)           # MT6701 (only top-side part besides C20)
    return b


def board_b():
    b = cyl(P.B_R, P.B_BOT, P.B_TOP)
    b = b - union_all([at_polar(cyl(1.1, P.B_BOT - 1, P.B_TOP + 1), P.B_HOLE_R, a) for a in P.B_HOLE_ANG])
    # a few tall parts from knob-main.kicad_pcb (positions may still change)
    usb = Pos(P.B_USB['x'] + 0.5, P.B_USB['y'], P.B_TOP) * Box(7.35, 8.94, P.B_USB['h'], align=MIN)
    esp = Pos(0, 22.75, P.B_TOP) * Box(18.0, 25.5, 3.1, align=MIN)
    xh = Pos(P.B_XH['x'] - 3.75, P.B_XH['y'], P.B_BOT - 7.0) * Box(12.4, 5.75, 7.0, align=MIN)
    return b + usb + esp + xh


def board_c():
    b = cyl(P.C_R, P.C_BACK, P.C_FRONT)
    b = b - union_all([at_polar(cyl(1.1, P.C_BACK - 1, P.C_FRONT + 1), P.C_HOLE_R, a) for a in P.C_HOLE_ANG])
    fh26 = Pos(-0.7, 4.38, P.C_FRONT) * Box(12.3, 4.4, 1.0, align=MIN)
    return b + fh26


def panel():
    g = cyl(P.GLASS_R, P.F - P.GLASS_T, P.F)
    mod = cyl(P.MODULE_R, P.F - P.PANEL_T, P.F - P.GLASS_T)
    back = cyl(21.0, P.F - P.PANEL_T - P.PANEL_BACK_EXTRA, P.F - P.PANEL_T)
    folds = [radial_box(P.MODULE_R - 1.0, P.MODULE_R + 0.9, 10.0,
                        P.F - P.PANEL_T - P.PANEL_BACK_EXTRA, P.F - P.GLASS_T, a) for a in P.FPC_ANG]
    return g + mod + back + union_all(folds)


def motor_stator():
    return ring(P.SHAFT_RO + 0.3, P.STATOR_R, P.MB_TOP, ROTOR_Z0_GAP())


def ROTOR_Z0_GAP():
    return P.ROTOR_Z0 - 0.15


def motor_rotor():
    """Rotating parts of the motor: bell, hollow shaft, magnet (assumed shapes)."""
    bell = ring(P.SHAFT_RO, P.ROTOR_R, P.ROTOR_Z0, P.ROTOR_Z1)
    shaft = ring(P.SHAFT_RI, P.SHAFT_RO, P.MAGNET['z0'], P.SHAFT_TOP)
    mag = ring(P.SHAFT_RO - 0.01, P.MAGNET['r_o'], P.MAGNET['z0'], P.MAGNET['z1'] - 0.15)
    return bell + shaft + mag


def machine_sheet(variant='classic', t=1.0, drop=70.0, half_w=70.0):
    """Stand-in for the machine's front-panel sheet sitting in the groove
    (outer face on the groove's long wall, top edge just below the groove end)."""
    prof = P.STOCK_PROFILES[variant]
    M, T = (prof[1], prof[2]) if variant == 'classic' else (prof[2], prof[3])
    uy, uz = T[0] - M[0], T[1] - M[1]
    L = math.hypot(uy, uz)
    uy, uz = uy / L, uz / L
    ny, nz = uz, -uy                                  # towards the case body
    a = (T[0] - 0.1 * uy - 0.05 * ny, T[1] - 0.1 * uz - 0.05 * nz + P.BLOCK_DZ)
    b = (a[0] - drop * uy, a[1] - drop * uz)
    c = (b[0] - t * ny, b[1] - t * nz)
    d = (a[0] - t * ny, a[1] - t * nz)
    return extrude(Plane.YZ * Polygon(a, b, c, d, align=None), amount=half_w, both=True)


def wire_bundle():
    """Envelope of the 13 screen wires (+3 motor wires if routed the same way):
    MountBase channel -> across board A under the front-case deck -> slot -> board B."""
    a = P.A_SLOT['ang']
    inner = radial_box(4.5, P.MB['r'] + 0.5, 3.4, 1.7, 2.6, a)
    across = radial_box(P.MB['r'] + 0.5, P.A_SLOT['r'] - 1.0, 5.0, 0.05, 2.6, a)
    drop = Rot(0, 0, a) * Pos(P.A_SLOT['r'], 0, P.B_TOP + 0.05) * Box(2.4, 6.0, -P.B_TOP + 2.55 - 0.05, align=MIN)
    return inner + across + drop
