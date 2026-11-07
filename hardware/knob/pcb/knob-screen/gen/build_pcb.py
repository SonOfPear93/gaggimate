"""Board C: place footprints from the schematic netlist, outline, keep-outs, export DSN for Freerouting.
Run with KiCad's python:  .../Python.framework/Versions/3.9/bin/python3 build_pcb.py <netlist> <out.kicad_pcb> <out.dsn>"""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'knob-main', 'gen'))
import pcbnew
from kgen_pcb import *

netlist, out_pcb, out_dsn = sys.argv[1:4]
CX, CY = 100.0, 100.0          # board centre
R = 23.0                       # Ø46 mm
# FH26 origin copied from Waveshare 3D model (connector pad-pattern centre at (-0.49, -4.38) rel. panel centre),
# biased 0.2 mm towards the panel edge so the FPC tail has slack rather than being short.
J1X, J1Y = CX - 0.7, CY - 4.38

place = {
    'J1': (J1X, J1Y, 0, 'F'),
    'J2': (CX, CY, 0, 'B'),
    'C3': (CX + 2.45, CY - 2.0, 90, 'F'),
    'C2': (CX + 3.55, CY - 2.0, 90, 'F'),
    'C1': (CX + 4.9, CY - 2.0, 90, 'F'),
    'C4': (CX + 2.45, CY - 5.6, 90, 'F'),
    'TP1': (CX + 3.6, CY - 9.0, 0, 'F'),
}
HOLES = [(0, -19.5), (-16.887, 9.75), (16.887, 9.75)]
for i, (hx, hy) in enumerate(HOLES):
    place['H%d' % (i + 1)] = (CX + hx, CY + hy, 0, 'F')

b, comps, nets = build(out_pcb, netlist, place, {'knob-screen': os.path.join(HERE, '..', 'knob-screen.pretty')},
                       layers=2, thickness=1.0)
add_circle_outline(b, CX, CY, R)
b.GetDesignSettings().SetAuxOrigin(P(CX, CY))
b.GetDesignSettings().SetGridOrigin(P(CX, CY))

# FPC tail corridor: keep parts out (FPC lies on top of the board here), tracks/vias allowed.
fpc = [(CX - 23.5, J1Y - 5.0), (J1X - 1.9, J1Y - 5.0), (J1X - 1.9, J1Y + 5.0), (CX - 23.5, J1Y + 5.0)]
# (documented in README; no rule area so the autorouter may still run tracks under the FPC)

# Silkscreen
FS, BS = pcbnew.F_SilkS, pcbnew.B_SilkS
add_text(b, 'GaggiMate Knob C', CX + 9.5, CY + 2.5, FS, 1.0)
add_text(b, 'knob-screen r1', CX + 9.5, CY + 4.2, FS, 0.8)
add_text(b, 'PANEL FPC', CX - 12.0, J1Y - 6.2, FS, 0.8)
add_line(b, CX - 16.5, J1Y, CX - 4.2, J1Y, FS, 0.15)
add_line(b, CX - 4.2, J1Y, CX - 5.2, J1Y - 0.6, FS, 0.15)
add_line(b, CX - 4.2, J1Y, CX - 5.2, J1Y + 0.6, FS, 0.15)
legend = ['1 3V3_LCD', '2 GND', '3 LCD_CS', '4 LCD_CLK', '5 LCD_D0', '6 LCD_D1', '7 LCD_D2',
          '8 LCD_D3', '9 LCD_RST', '10 TP_SDA', '11 TP_SCL', '12 TP_INT', '13 TP_RST']
for i, s_ in enumerate(legend):
    col, row = (0, i) if i < 7 else (1, i - 7)
    add_text(b, s_, CX + (4.5 if col == 0 else -4.5), CY + 9.2 + row * 1.05, BS, 0.7, mirror=True, thick=0.12)
add_text(b, 'WIRES -> board B J7 (same numbers)', CX, CY + 17.4, BS, 0.8, mirror=True)
add_text(b, 'GaggiMate knob-screen r1', CX, CY + 18.9, BS, 0.8, mirror=True)
tidy_silk(b)

pcbnew.SaveBoard(out_pcb, b)
print('saved', out_pcb, out_dsn)
