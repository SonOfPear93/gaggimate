"""Board B after autorouting: remove routing debris, outer-layer pours, stitching vias, fill, tidy silk."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from kgen_pcb import *
pcb = sys.argv[1]
CX, CY, R = 100.0, 100.0, 37.0
b = pcbnew.LoadBoard(pcb)
print('dangling removed:', remove_dangling(b))
for z in list(b.Zones()):
    if not z.GetIsRuleArea() and z.GetLayer() in (pcbnew.F_Cu, pcbnew.B_Cu):
        b.Remove(z); GRAVE.append(z)
circ = circle_pts(CX, CY, R - 0.4, 120)
# outer layers: GND pour (the ESP32 footprint rule area keeps the antenna region copper-free on all layers)
add_zone(b, '/GND', pcbnew.F_Cu, circ, clearance=0.25, minw=0.25, name='GND_TOP')
add_zone(b, '/GND', pcbnew.B_Cu, circ, clearance=0.25, minw=0.25, name='GND_BOT')
# LDO tab (U3 AP7361C-33ER pin 2 = VO = +3V3) heat-spreading copper on top, higher priority than the GND pour
u3 = b.FindFootprintByReference('U3')
ux, uy = pcbnew.ToMM(u3.GetPosition().x), pcbnew.ToMM(u3.GetPosition().y)
add_zone(b, '/+3V3', pcbnew.F_Cu, [(ux + 1.2, uy - 4.6), (ux + 6.0, uy - 4.6), (ux + 6.0, uy + 4.6), (ux + 1.2, uy + 4.6)],
         clearance=0.25, minw=0.25, priority=5, name='LDO_TAB')
fill_zones(b)
# stitching vias: GND around the board (skips anything too close to other copper / keep-outs)
cand = []
for r, n in ((35.2, 64), (31.0, 56), (26.0, 46), (20.0, 36), (14.0, 26), (8.0, 16)):
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        cand.append((CX + r * math.cos(a), CY + r * math.sin(a)))
print('GND stitch vias:', stitch(b, '/GND', cand, 0.6, 0.3, 0.3))
# extra +3V3 vias under the LDO tab copper
tab = [(ux + 4.6, uy + dy) for dy in (-3.4, -1.7, 1.7, 3.4)] + [(ux + 5.5, uy + dy) for dy in (-2.6, 0, 2.6)]
print('LDO tab vias:', stitch(b, '/+3V3', tab, 0.6, 0.3, 0.25))
tidy_silk(b, hide_prefixes=('R', 'C', 'Q', 'D'))
for ref in ('U2', 'U4', 'J6', 'J7'):
    b.FindFootprintByReference(ref).Reference().SetVisible(False)
# bottom wire legend: 1.3 mm line pitch
leg = sorted([t for t in b.GetDrawings() if t.GetClass() == 'PCB_TEXT' and t.GetLayer() == pcbnew.B_SilkS], key=lambda t: t.GetPosition().y)
for i, t in enumerate(leg):
    t.SetPosition(P(CX - 9.0, CY + 1.0 + i * 1.3))
fill_zones(b)
pcbnew.SaveBoard(pcb, b)
print('finished', pcb)
