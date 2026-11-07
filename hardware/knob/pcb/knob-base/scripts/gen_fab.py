#!/usr/bin/env python3
"""Fabrication outputs for knob-base (JLCPCB): Gerbers + drill zip, BOM, CPL, renders, reports.

Run with KiCad 10's bundled Python after gen_pcb.py:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 scripts/gen_fab.py

CPL rotation follows kicad-jlcpcb-tools (fabrication.py): bottom-side angles are
mirrored as (180 - rot), then a per-package correction is added. Corrections used
are the plugin's database values for SOIC (270) and SOT-23 (-90); the JST SH
horizontal header uses 180 by analogy with the plugin's JST_GH_SM / JST_PH_S
entries and MUST be checked in JLC's placement preview before ordering.
"""
from pathlib import Path
import csv
import re
import shutil
import subprocess
import zipfile

import pcbnew as pcb
import wx

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
NAME = 'knob-base'
BOARD = PROJ / (NAME + '.kicad_pcb')
SCH = PROJ / (NAME + '.kicad_sch')
FAB = PROJ / 'fab'
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
CORRECTIONS = [(r'^SOIC-', 270), (r'^SOT-23', -90), (r'^JST_SH_SM', 180)]


def run(*args):
    subprocess.run([CLI, *args], check=True, capture_output=True)


def main():
    if FAB.exists():
        shutil.rmtree(FAB)
    gdir = FAB / 'gerbers'
    gdir.mkdir(parents=True)
    run('pcb', 'export', 'gerbers', str(BOARD), '-o', str(gdir) + '/',
        '--layers', 'F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts',
        '--subtract-soldermask')
    run('pcb', 'export', 'drill', str(BOARD), '-o', str(gdir) + '/', '--format', 'excellon',
        '--drill-origin', 'absolute', '--excellon-units', 'mm', '--excellon-separate-th',
        '--generate-map', '--map-format', 'gerberx2')
    with zipfile.ZipFile(FAB / f'{NAME}-gerbers.zip', 'w', zipfile.ZIP_DEFLATED) as z:
        for f in sorted(gdir.iterdir()):
            z.write(f, f.name)

    app = wx.App(False)
    board = pcb.LoadBoard(str(BOARD))
    groups = {}
    cpl = []
    for fp in sorted(board.GetFootprints(), key=lambda f: (re.sub(r'\d+', '', f.GetReference()),
                                                          int(re.sub(r'\D', '', f.GetReference()) or 0))):
        ref = fp.GetReference()
        if fp.IsExcludedFromBOM() and fp.IsExcludedFromPosFiles():
            continue
        lcsc = fp.GetFieldText('LCSC') if fp.HasField('LCSC') else ''
        assert lcsc.startswith('C'), (ref, lcsc)
        pkg = str(fp.GetFPID().GetLibItemName())
        key = (fp.GetValue(), pkg, lcsc)
        groups.setdefault(key, []).append(ref)
        pads = list(fp.Pads())
        bb = pads[0].GetBoundingBox()
        for p in pads:
            bb.Merge(p.GetBoundingBox())
        c = bb.GetCenter()
        rot = fp.GetOrientationDegrees()
        bottom = fp.IsFlipped()
        if bottom:
            rot = (180 - rot) % 360
        for rx, corr in CORRECTIONS:
            if re.search(rx, pkg):
                rot = (rot + corr) % 360
                break
        cpl.append((ref, f'{pcb.ToMM(c.x):.4f}mm', f'{-pcb.ToMM(c.y):.4f}mm', 'Bottom' if bottom else 'Top',
                    f'{rot % 360:g}'))
    with open(FAB / f'{NAME}-BOM-JLC.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #'])
        for (val, pkg, lcsc), refs in groups.items():
            w.writerow([val, ','.join(refs), pkg, lcsc])
    with open(FAB / f'{NAME}-CPL-JLC.csv', 'w', newline='') as f:
        w = csv.writer(f)
        w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
        w.writerows(cpl)
    app.Destroy()

    for side in ('top', 'bottom'):
        run('pcb', 'render', str(BOARD), '--side', side, '-w', '1600', '-h', '1600', '--quality', 'high',
            '-o', str(FAB / f'{NAME}-{side}.png'))
    run('sch', 'export', 'pdf', str(SCH), '-o', str(FAB / f'{NAME}-schematic.pdf'))
    run('sch', 'erc', str(SCH), '-o', str(FAB / 'erc-report.txt'))
    run('pcb', 'drc', str(BOARD), '--schematic-parity', '-o', str(FAB / 'drc-report.txt'))
    print('fab outputs in', FAB)


if __name__ == '__main__':
    main()
