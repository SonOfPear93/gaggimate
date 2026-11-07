"""Import a Freerouting SES into a board: ses.py board.kicad_pcb in.ses"""
import sys, pcbnew
b = pcbnew.LoadBoard(sys.argv[1])
assert pcbnew.ImportSpecctraSES(b, sys.argv[2])
pcbnew.ZONE_FILLER(b).Fill(b.Zones())
b.BuildConnectivity()
print('unconnected', b.GetConnectivity().GetUnconnectedCount(False))
pcbnew.SaveBoard(sys.argv[1], b)
