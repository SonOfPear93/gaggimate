"""Board B: place footprints from the schematic netlist, outline, planes, keep-outs.
Run with KiCad's python: build_pcb.py <netlist> <out.kicad_pcb>"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from kgen_pcb import *

netlist, out_pcb = sys.argv[1:3]
CX, CY = 100.0, 100.0
R = 37.0                                   # Ø74 mm
s2 = math.sqrt(0.5)

# Wire cluster under board A's slot (r=33.5 mm, 225 deg front view = lower-left here; front view == B top view).
# u = radial unit vector at 225 deg, t = tangent.  J7 row A (pads 1-7) at r=29, row B (8-13) at r=27; J6 motor pads at r=31.5
u = (-s2, s2); t = (s2, s2)
J7O = (29.0 * u[0], 29.0 * u[1])
J6C = (32.0 * u[0], 32.0 * u[1])
J6P1 = (J6C[0] - 2.54 * t[0], J6C[1] - 2.54 * t[1])
HOLE_ANG = (22.5, 112.5, 202.5, 292.5)
HOLES = [(33.0 * math.cos(math.radians(a)), -33.0 * math.sin(math.radians(a))) for a in HOLE_ANG]

PL = {
    # --- MCU ---
    'U1': (0, -22.75, 0),
    'C6': (-11.0, -26.9, 90), 'C5': (-11.0, -22.6, 90),
    'R3': (-12.6, -24.6, 90), 'C7': (-14.0, -24.6, 90), 'SW1': (-16.0, -16.6, 0),
    'R4': (12.6, -8.6, 0), 'SW2': (17.5, -8.0, 0),
    'R5': (5.6, -7.6, 0), 'D3': (8.4, -7.6, 180),
    'TP4': (13.0, -27.6, 0), 'TP5': (15.6, -27.6, 0),
    'TP1': (15.6, -14.2, 0), 'TP2': (18.2, -14.2, 0), 'TP3': (20.8, -14.2, 0),
    'R21': (11.9, -16.6, 0), 'R22': (11.9, -17.85, 0), 'R23': (11.9, -19.1, 0),
    # --- USB / power in ---
    # USB-C at 180 deg (board -X), axis-aligned: mating face (footprint y=+3.65) at x=-36.85, i.e. flush with the
    # Ø74 edge (centre 0.15 mm inside, shell corners 0.12 mm outside)
    'J1': (-33.2, 0.0, 270), 'U2': (-24.6, 0.0, 90),
    'R1': (-26.6, -4.9, 0), 'R2': (-26.6, 4.9, 0),
    'D1': (-25.5, -8.6, 0), 'C1': (-20.2, -8.6, 90),
    'J2': (16.0, 10.0, 0, 'B'), 'D2': (21.0, 14.6, 0),
    'TP6': (18.5, 6.4, 0), 'TP7': (21.0, 6.4, 0),
    'U3': (26.0, -2.0, 0), 'C2': (21.4, 3.4, 0), 'C3': (31.4, -1.2, 90), 'C4': (31.4, 2.2, 90),
    # --- board A link: under board A's J1 (front view (-10,-29.5) -> here (-10, 29.5)), opening towards the centre
    'J8': (-10.0, 29.5, 180),
    # --- display ---
    'R6': (-6.0, -6.2, 0), 'R7': (-6.0, -5.0, 0), 'R8': (-6.0, -3.8, 0), 'R9': (-6.0, -2.6, 0),
    'R10': (-6.0, -1.4, 0), 'R11': (-6.0, -0.2, 0),
    'R12': (-11.0, 15.5, 90), 'R13': (-9.8, 15.5, 90),
    'Q1': (-23.0, 6.5, 0), 'R14': (-20.0, 4.0, 0), 'C8': (-20.0, 5.2, 0), 'R15': (-17.6, 6.5, 90),
    'Q2': (-15.0, 6.5, 0), 'R16': (-15.0, 9.4, 0), 'C9': (-21.2, 9.6, 0),
    'J7': (J7O[0], J7O[1], 135),
    'J6': (J6P1[0], J6P1[1], 45),
    # --- motor (U4 at (6,16); local parts keep their offsets relative to U4) ---
    'U4': (6.0, 16.0, 0),
    'C12': (2.2, 16.8, 180), 'C13': (3.6, 19.3, 0), 'C16': (-1.0, 18.2, 180),
    'C17': (-1.6, 21.0, 0), 'C14': (-1.6, 23.6, 0), 'C15': (-6.4, 23.6, 0),
    'C10': (1.5, 14.6, 0), 'C11': (10.0, 15.6, 0),
    'R17': (1.5, 13.2, 0), 'R18': (4.0, 12.4, 90), 'R19': (9.6, 13.0, 0), 'R20': (6.6, 12.4, 90),
    'J5': (4.0, 27.0, 0),
}
for i, (hx, hy) in enumerate(HOLES):
    PL['H%d' % (i + 1)] = (hx, hy, 0)
place = {}
for k, v in PL.items():
    side = v[3] if len(v) > 3 else 'F'
    place[k] = (CX + v[0], CY + v[1], v[2], side)

b, comps, nets = build(out_pcb, netlist, place, {'knob-main': os.path.join(HERE, '..', 'knob-main.pretty')},
                       layers=4, thickness=1.6)
b.SetLayerType(pcbnew.In1_Cu, pcbnew.LT_POWER)
b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_POWER)
add_circle_outline(b, CX, CY, R)
ds = b.GetDesignSettings()
ds.SetAuxOrigin(P(CX, CY)); ds.SetGridOrigin(P(CX, CY))

# DRV8311 exposed pad: 4 thermal vias (0.3 mm drill) to the inner GND plane
for dx, dy in ((-0.45, -0.45), (0.45, -0.45), (-0.45, 0.45), (0.45, 0.45)):
    add_via(b, '/GND', CX + PL['U4'][0] + dx, CY + PL['U4'][1] + dy, 0.5, 0.3)

# Planes: In1 = GND, In2 = +3V3 (whole board; ESP32 antenna keep-out comes from the module footprint rule area)
circ = circle_pts(CX, CY, R - 0.4, 120)
add_zone(b, '/GND', pcbnew.In1_Cu, circ, clearance=0.2, minw=0.2, name='GND_PLANE')
add_zone(b, '/+3V3', pcbnew.In2_Cu, circ, clearance=0.2, minw=0.2, name='3V3_PLANE')

# Silkscreen
FS, BS = pcbnew.F_SilkS, pcbnew.B_SilkS
add_text(b, 'GaggiMate Knob B', CX + 24.0, CY + 17.0, FS, 1.0, rot=0)
add_text(b, 'knob-main r1', CX + 24.0, CY + 18.7, FS, 0.8)
# wire legend next to the cluster
leg = ['SCREEN WIRES (J7 = board C J2)', '1 3V3_LCD 2 GND 3 CS 4 CLK', '5 D0 6 D1 7 D2 8 D3 9 LCD_RST',
       '10 TP_SDA 11 TP_SCL 12 TP_INT 13 TP_RST', 'J6 MOTOR: 1 A  2 B  3 C']
for i, txt in enumerate(leg):
    tt = add_text(b, txt, CX - 9.0, CY + 1.0 + i * 1.3, BS, 0.8, thick=0.12, mirror=True)

pcbnew.SaveBoard(out_pcb, b)
print('saved', out_pcb)
