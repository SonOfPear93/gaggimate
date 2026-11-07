"""Board C: clean up after routing, GND pours on both layers + stitching vias, fill, save."""
import os, sys, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'knob-main', 'gen'))
import pcbnew
from kgen_pcb import *
pcb = sys.argv[1]
b = pcbnew.LoadBoard(pcb)
print('dangling removed:', remove_dangling(b))
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z); GRAVE.append(z)
pts = circle_pts(100, 100, 22.6, 90)
add_zone(b, '/GND', pcbnew.F_Cu, pts, clearance=0.2, minw=0.2)
add_zone(b, '/GND', pcbnew.B_Cu, pts, clearance=0.2, minw=0.2)
cand = []
for r, n in ((10.0, 10), (14.0, 14), (18.0, 18), (21.5, 22)):
    for i in range(n):
        a = 2 * math.pi * (i + 0.5) / n
        cand.append((100 + r * math.cos(a), 100 + r * math.sin(a)))
print('stitch vias:', stitch(b, '/GND', cand, 0.6, 0.3, 0.3))
fill_zones(b)
pcbnew.SaveBoard(pcb, b)
print('filled', pcb)
