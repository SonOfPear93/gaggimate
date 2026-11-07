#!/usr/bin/env python3
"""Build every part and export STEP + STL.

  out/step/*.step        printed parts, assembly position (case frame)
  out/stl/*.stl          same, assembly position
  out/print/*.stl        printed parts in print orientation (on z = 0)
  out/standins/*.stl     non-printed stand-ins (boards, panel, motor, RotorSpacer)

Usage: python build.py            (all)
       python build.py knob       (only parts whose name contains 'knob')
"""
import sys
import time
from pathlib import Path

import trimesh
from build123d import Pos, Rot, export_step, export_stl

from knobcad import parts as K
from knobcad import params as P

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'

# name -> (builder, in board frame?, print flip about X?)
PRINTED = {
    'knob_ring':                 (K.knob, True, True),
    'screen_platform':           (K.screen_platform, True, False),
    'mount_base':                (K.mountbase, True, False),
    'front_case':                (K.front_case, True, True),
    'back_case_classic':         (lambda: K.back_case('classic'), False, False),
    'back_case_classic_pro':     (lambda: K.back_case('classic_pro'), False, False),
}
STANDINS = {
    'board_a': (K.board_a, True),
    'board_b': (K.board_b, True),
    'board_c': (K.board_c, True),
    'panel': (K.panel, True),
    'motor_stator': (K.motor_stator, True),
    'motor_rotor': (K.motor_rotor, True),
    'wire_bundle': (K.wire_bundle, True),
    'machine_sheet_classic': (lambda: K.machine_sheet('classic'), False),
    'machine_sheet_classic_pro': (lambda: K.machine_sheet('classic_pro'), False),
}


def export(part, name, folder, step=True):
    (OUT / folder).mkdir(parents=True, exist_ok=True)
    if step:
        (OUT / 'step').mkdir(parents=True, exist_ok=True)
        export_step(part, str(OUT / 'step' / f'{name}.step'))
    export_stl(part, str(OUT / folder / f'{name}.stl'), tolerance=0.01, angular_tolerance=0.1)


def main(filt=None):
    report = []
    for name, (fn, board, flip) in PRINTED.items():
        if filt and filt not in name:
            continue
        t = time.time()
        p = fn()
        if board:
            p = K.to_case(p)
        export(p, name, 'stl')
        q = Rot(180, 0, 0) * p if flip else p
        q = Pos(0, 0, -q.bounding_box().min.Z) * q
        export(q, name, 'print', step=False)
        bb = p.bounding_box()
        report.append(f'{name:24s} vol {p.volume/1000:6.1f} cm3  bbox x[{bb.min.X:.1f},{bb.max.X:.1f}] '
                      f'y[{bb.min.Y:.1f},{bb.max.Y:.1f}] z[{bb.min.Z:.2f},{bb.max.Z:.2f}]  '
                      f'valid={p.is_valid}  {time.time()-t:.1f}s')
        print(report[-1], flush=True)
    for name, (fn, board) in STANDINS.items():
        if filt and filt not in name:
            continue
        p = fn()
        if board:
            p = K.to_case(p)
        export(p, name, 'standins', step=False)
    if not filt or 'spacer' in (filt or ''):
        # SmartKnob RotorSpacer, reused unchanged; placed rotated like the rest of the stack
        m = trimesh.load(HERE / 'reused' / 'RotorSpacer.stl')
        m.apply_transform(trimesh.transformations.rotation_matrix(
            __import__('math').radians(P.SPACER_LOBE_ANG0 + P.STACK_ROT), [0, 0, 1]))
        (OUT / 'standins').mkdir(parents=True, exist_ok=True)
        m.export(OUT / 'standins' / 'rotor_spacer_smartknob.stl')
    (OUT / 'build_report.txt').write_text('\n'.join(report) + '\n') if not filt else None


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else None)
