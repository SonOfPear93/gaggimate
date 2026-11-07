"""Board B: drop vias for every SMD GND/+3V3 pad to the inner planes before autorouting."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from kgen_pcb import *
pcb = sys.argv[1]
b = pcbnew.LoadBoard(pcb)
# DRV8311 PGND (pin 9) and AGND (pin 16) straight into the exposed pad (which has 4 vias to the GND plane)
u4 = b.FindFootprintByReference('U4')
ux, uy = pcbnew.ToMM(u4.GetPosition().x), pcbnew.ToMM(u4.GetPosition().y)
add_track(b, '/GND', pcbnew.F_Cu, [(ux - 0.27, uy + 1.465), (ux - 0.27, uy + 0.5)], 0.2)
add_track(b, '/GND', pcbnew.F_Cu, [(ux + 1.465, uy), (ux + 0.5, uy)], 0.2)
F = pcbnew.F_Cu
def T(net, pts, w):
    add_track(b, net, F, [(ux + x, uy + y) for (x, y) in pts], w)
# +5V island: VIN_AVDD (p7) + VM (p8) + CP cap + VM/VIN caps
T('/+5V', [(-1.465, 1.2), (-2.1, 1.2), (-2.1, 2.2)], 0.2)
T('/+5V', [(-0.67, 1.465), (-0.67, 2.2)], 0.2)
T('/+5V', [(-0.67, 2.2), (-2.1, 2.2), (-3.0, 2.2)], 0.3)
T('/+5V', [(-3.0, 2.2), (-3.175, 3.3)], 0.3)                                   # to C13 pad1 (+5V)
T('/+5V', [(-3.0, 2.2), (-6.52, 2.2)], 0.3)                                    # to C16 pad1 (+5V)
T('/+5V', [(-4.575, 0.8), (-4.575, 2.2)], 0.3)                                 # C12 pad2 (+5V)
# charge pump: p6 straight left into C12 pad1 (C12 rot 180 at (-3.8, 0.8))
T('/DRV_CP', [(-1.465, 0.8), (-3.025, 0.8)], 0.2)
# SOB jogs into the unused SOC (pin 3) channel, SOA follows below it; both escape left to vias
T('/DRV_SOB', [(-1.465, 0.0), (-1.85, 0.0), (-2.2, -0.35), (-6.3, -0.35)], 0.2)
add_via(b, '/DRV_SOB', ux - 6.3, uy - 0.35, 0.6, 0.3)
T('/DRV_SOA', [(-1.465, 0.4), (-1.95, 0.4), (-2.35, 0.0), (-5.65, 0.0), (-5.65, 0.65)], 0.2)
add_via(b, '/DRV_SOA', ux - 5.65, uy + 0.65, 0.6, 0.3)
# INHA/INHB/INHC escape right to staggered vias
T('/DRV_INHA', [(1.465, 0.4), (3.0, 0.4)], 0.2)
add_via(b, '/DRV_INHA', ux + 3.0, uy + 0.4, 0.6, 0.3)
T('/DRV_INHB', [(1.465, 0.8), (2.2, 0.8), (2.6, 1.5)], 0.2)
add_via(b, '/DRV_INHB', ux + 2.6, uy + 1.5, 0.6, 0.3)
T('/DRV_INHC', [(1.465, 1.2), (1.95, 1.2), (1.95, 1.9), (2.1, 2.6)], 0.2)
add_via(b, '/DRV_INHC', ux + 2.1, uy + 2.6, 0.6, 0.3)
# motor outputs fanned out to J5 (Motor class width after the fan)
T('/MOT_A', [(0.13, 1.465), (0.13, 2.3), (-0.4, 2.83), (-0.4, 4.5)], 0.2)
T('/MOT_B', [(0.53, 1.465), (0.53, 4.5)], 0.2)
T('/MOT_C', [(0.93, 1.465), (0.93, 2.3), (1.46, 2.83), (1.46, 4.5)], 0.2)
T('/MOT_A', [(-0.4, 4.4), (-0.4, 5.0), (-3.25, 5.0), (-3.25, 8.6)], 0.5)
T('/MOT_B', [(0.53, 4.4), (0.53, 5.9), (-2.0, 5.9), (-2.0, 8.6)], 0.5)
T('/MOT_C', [(1.46, 3.4), (1.46, 6.8), (-0.75, 6.8), (-0.75, 8.6)], 0.5)
# C13 (VM decoupling) GND pad: via just below it
T('/GND', [(-1.625, 3.3), (-1.625, 4.15)], 0.3)
add_via(b, '/GND', ux - 1.625, uy + 4.15, 0.6, 0.3)
# INLA/INLB/INLC all = DRV_EN
T('/DRV_EN', [(1.465, -1.2), (2.3, -1.2), (2.3, -0.8), (1.465, -0.8)], 0.2)
T('/DRV_EN', [(0.93, -1.465), (0.93, -2.0), (2.3, -2.0), (2.3, -1.2)], 0.2)
# AVDD p17 -> C11 pad1
T('/DRV_AVDD', [(1.465, -0.4), (3.52, -0.4)], 0.2)
# USB-C GND contacts (A1/B12 and B1/A12 pairs) -> nearest shield THT pad (the shield is on the inner GND plane)
j1 = b.FindFootprintByReference('J1')
sh_pads = [p for p in j1.Pads() if p.GetNumber() == 'SH']
for p in j1.Pads():
    if p.GetNumber() in ('A1', 'B12', 'B1', 'A12'):
        q = min(sh_pads, key=lambda h: (h.GetPosition() - p.GetPosition()).EuclideanNorm())
        a, c = p.GetPosition(), q.GetPosition()
        add_track(b, '/GND', pcbnew.F_Cu, [(pcbnew.ToMM(a.x), pcbnew.ToMM(a.y)), (pcbnew.ToMM(c.x), pcbnew.ToMM(c.y))], 0.3)
done, failed = fanout(b, ('/GND', '/+3V3'), (100, 100), 37.0, 0.6, 0.3, 0.2, 0.35)
print('fanout vias', done, 'failed', failed)
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
print('unconnected after fanout', b.GetConnectivity().GetUnconnectedCount(False))
pcbnew.SaveBoard(pcb, b)
