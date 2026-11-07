"""Export a Specctra DSN for Freerouting: dsn.py board.kicad_pcb out.dsn
Copper zones are dropped from the DSN (Freerouting treats full-board planes as obstacles for vias); GND/+3V3
reach the inner planes through pre-placed fan-out vias (prefan.py) and their class 'Plane' is ignored by the router.
Clearances get +0.012 mm margin (Freerouting rounding near rotated pads)."""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
keep = []
for z in list(b.Zones()):
    if not z.GetIsRuleArea():
        b.Remove(z); keep.append(z)
ns = b.GetDesignSettings().m_NetSettings
for nc in [ns.GetDefaultNetclass()] + [v for k, v in ns.GetNetclasses().items()]:
    nc.SetClearance(nc.GetClearance() + pcbnew.FromMM(0.012))
if '--in2-signal' in sys.argv:
    # completion pass: let the router use In2 (the +3V3 plane layer) for the few leftovers; the +3V3 pour flows around them
    b.SetLayerType(pcbnew.In2_Cu, pcbnew.LT_SIGNAL)
assert pcbnew.ExportSpecctraDSN(b, sys.argv[2])
print('dsn', sys.argv[2])
