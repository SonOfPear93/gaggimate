"""Autoroute a board with Freerouting: route.py board.kicad_pcb work_dir freerouting.jar [passes] [tries]
Loads the board (with its .kicad_pro so net classes apply), exports DSN, runs Freerouting headless, imports SES.
Freerouting 2.x is multi-threaded and not deterministic, so retry until nothing is left unrouted."""
import sys, os, subprocess, time, shutil
import pcbnew
pcb, work, jar = sys.argv[1:4]
passes = sys.argv[4] if len(sys.argv) > 4 else '40'
tries = int(sys.argv[5]) if len(sys.argv) > 5 else 4
base = os.path.join(work, os.path.splitext(os.path.basename(pcb))[0])
src = base + '.unrouted.kicad_pcb'
shutil.copy(pcb, src)
best = None
for attempt in range(tries):
    b = pcbnew.LoadBoard(pcb)
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    # route with +0.012 mm clearance margin (Freerouting rounds near rotated pads)
    ns = b.GetDesignSettings().m_NetSettings
    ncs = [ns.GetDefaultNetclass()] + [v for k, v in ns.GetNetclasses().items()]
    for nc in ncs:
        nc.SetClearance(nc.GetClearance() + pcbnew.FromMM(0.012))
    dsn, ses = base + '.dsn', base + '.ses'
    if os.path.exists(ses):
        os.remove(ses)
    assert pcbnew.ExportSpecctraDSN(b, dsn)
    t = time.time()
    cmd = ['java', '-jar', jar, '-de', dsn, '-do', ses, '-mp', passes, '--gui.enabled=false']
    r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    open(base + '.frlog', 'w').write(r.stdout)
    assert os.path.exists(ses), 'no SES produced'
    assert pcbnew.ImportSpecctraSES(b, ses)
    b.BuildConnectivity()
    pcbnew.ZONE_FILLER(b).Fill(b.Zones())
    b.BuildConnectivity()
    unc = b.GetConnectivity().GetUnconnectedCount(False)
    print('attempt %d: %.0fs, unconnected=%d' % (attempt + 1, time.time() - t, unc), flush=True)
    if best is None or unc < best:
        best = unc
        pcbnew.SaveBoard(base + '.best.kicad_pcb', b)
    if unc == 0:
        break
    # restore unrouted copy for the next attempt
    shutil.copy(src, pcb)
shutil.copy(base + '.best.kicad_pcb', pcb)
print('routed + saved', pcb, 'unconnected', best)
