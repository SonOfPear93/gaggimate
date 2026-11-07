"""Fab outputs for JLCPCB: Gerbers+drill zip, BOM CSV, CPL CSV, 3D renders.
Usage (KiCad python): fab.py board.kicad_pcb fab_dir
CPL logic mirrors kicad-jlcpcb-tools (pad-bbox centre, Y up, rotation corrections, bottom = 180-rot)."""
import os, sys, re, csv, subprocess, zipfile, glob, math
import pcbnew

KCLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
pcb, fab = sys.argv[1], sys.argv[2]
name = os.path.splitext(os.path.basename(pcb))[0]
os.makedirs(fab, exist_ok=True)

# Rotation corrections: copied from kicad-jlcpcb-tools corrections.db (the entries that matter here),
# plus two additions by analogy (JST SH / Molex PicoBlade right-angle SMD, same style as JST_GH_SM) - verify in JLC DFM preview.
CORR = [
    (r'^SOT-223', 180), (r'^SOT-23', -90), (r'^USB_C_Receptacle_HRO_TYPE-C-31-M-12', 180),
    (r'^(.*?_|V)?QFN-(16|20|24|28|40)(-|_|$)', 270),
    (r'^JST_SH_SM', 180), (r'^Molex_PicoBlade_53261', 180),
]


def corr(fp):
    for getter in (fp.GetReference, fp.GetValue, lambda: str(fp.GetFPID().GetLibItemName())):
        v = str(getter())
        for rx, rot in CORR:
            if re.search('(?:%s)$' % rx, v):
                return rot
        for rx, rot in CORR:
            if re.search(rx, v):
                return rot
    return 0


b = pcbnew.LoadBoard(pcb)
ao = b.GetDesignSettings().GetAuxOrigin()
rows_cpl, groups = [], {}
for fp in sorted(b.Footprints(), key=lambda f: (re.sub(r'\d+', '', f.GetReference()), int(re.sub(r'\D', '', f.GetReference()) or 0))):
    lcsc = fp.GetFieldText('LCSC') if fp.HasField('LCSC') else ''
    if not lcsc or fp.IsExcludedFromBOM() or fp.IsDNP():
        continue
    pads = list(fp.Pads())
    bb = pads[0].GetBoundingBox()
    for p in pads:
        bb.Merge(p.GetBoundingBox())
    c = bb.GetCenter()
    x = pcbnew.ToMM(c.x - ao.x)
    y = -pcbnew.ToMM(c.y - ao.y)
    rot = fp.GetOrientation().AsDegrees()
    bottom = fp.GetLayer() != pcbnew.F_Cu
    if bottom:
        rot = (180 - rot) % 360
    rot = (rot + corr(fp)) % 360
    rows_cpl.append([fp.GetReference(), '%.4f' % x, '%.4f' % y, 'Bottom' if bottom else 'Top', '%g' % rot])
    pkg = str(fp.GetFPID().GetLibItemName())
    key = (fp.GetValue(), pkg, lcsc)
    groups.setdefault(key, []).append(fp.GetReference())

with open(os.path.join(fab, name + '-CPL.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    w.writerows(rows_cpl)
with open(os.path.join(fab, name + '-BOM.csv'), 'w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC'])
    for (val, pkg, lcsc), refs in sorted(groups.items(), key=lambda kv: kv[1][0]):
        w.writerow([val, ','.join(refs), pkg, lcsc])

# Gerbers + drill
gdir = os.path.join(fab, 'gerber')
os.makedirs(gdir, exist_ok=True)
for f in glob.glob(os.path.join(gdir, '*')):
    os.remove(f)
nl = b.GetCopperLayerCount()
layers = ['F.Cu', 'B.Cu', 'F.Paste', 'B.Paste', 'F.SilkS', 'B.SilkS', 'F.Mask', 'B.Mask', 'Edge.Cuts']
if nl == 4:
    layers[2:2] = ['In1.Cu', 'In2.Cu']
subprocess.run([KCLI, 'pcb', 'export', 'gerbers', '-o', gdir + '/', '-l', ','.join(layers),
                '--subtract-soldermask', '--no-x2', '--use-drill-file-origin', pcb], check=True, stdout=subprocess.DEVNULL)
subprocess.run([KCLI, 'pcb', 'export', 'drill', '-o', gdir + '/', '--format', 'excellon', '--drill-origin', 'plot',
                '--excellon-units', 'mm', '--generate-map', '--map-format', 'gerberx2', pcb], check=True, stdout=subprocess.DEVNULL)
zp = os.path.join(fab, name + '-gerbers.zip')
with zipfile.ZipFile(zp, 'w', zipfile.ZIP_DEFLATED) as z:
    for f in sorted(glob.glob(os.path.join(gdir, '*'))):
        z.write(f, os.path.basename(f))
print('gerbers:', len(glob.glob(os.path.join(gdir, '*'))), 'files ->', zp)

# 3D renders
for side in ('top', 'bottom'):
    out = os.path.join(fab, '%s-render-%s.png' % (name, side))
    subprocess.run([KCLI, 'pcb', 'render', '--side', side, '--quality', 'high', '-w', '1600', '-h', '1600',
                    '--background', 'opaque', '--zoom', '1.0', '-o', out, pcb], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print('render', out, os.path.exists(out))
print('BOM lines', len(groups), 'CPL rows', len(rows_cpl))
