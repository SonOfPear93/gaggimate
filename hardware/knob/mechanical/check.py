#!/usr/bin/env python3
"""Interference + clearance check of the full assembly (run build.py first).

1. Pairwise boolean intersection (manifold3d) of every printed part and stand-in.
   Anything above 0.001 mm^3 is reported as an overlap.
2. Minimum distance between every rotating part (knob ring, RotorSpacer, motor
   rotor stand-in) and every stationary part; reported if below WARN_GAP.

Writes out/check_report.txt.
"""
import itertools
import sys
from pathlib import Path

import manifold3d as mf
import numpy as np
import trimesh

HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
WARN_GAP = 0.6
ROTATING = ('knob_ring', 'rotor_spacer_smartknob', 'motor_rotor')
# small gaps that come from SmartKnob's own design or from the assumed motor shape
KNOWN = {
    frozenset(('knob_ring', 'panel')): 'by spec: 0.5 mm radial gap round the cover glass',
    frozenset(('motor_rotor', 'mount_base')): 'SmartKnob: MountBase tube in the 5.9 mm shaft bore / magnet pocket',
    frozenset(('motor_rotor', 'motor_stator')): 'motor stand-ins (assumed shapes)',
    frozenset(('rotor_spacer_smartknob', 'motor_stator')): 'motor stand-ins (assumed shapes)',
}


def to_manifold(m):
    mesh = mf.Mesh(vert_properties=np.asarray(m.vertices, np.float32),
                   tri_verts=np.asarray(m.faces, np.uint32))
    return mf.Manifold(mesh)


def load_set(variant):
    files = {f.stem: f for f in (OUT / 'stl').glob('*.stl')}
    files.update({f.stem: f for f in (OUT / 'standins').glob('*.stl')})
    other = 'classic_pro' if variant == 'classic' else 'classic'
    files.pop('back_case_' + other, None)
    files.pop('machine_sheet_' + other, None)
    meshes = {}
    for n, f in sorted(files.items()):
        m = trimesh.load(f)
        m.merge_vertices()
        meshes[n] = m
    return meshes


def min_distance(a, b, n=40000):
    """Approximate min distance between two meshes (sampled both ways)."""
    best = np.inf
    for src, dst in ((a, b), (b, a)):
        pts = np.vstack([src.vertices, src.sample(n)])
        # cheap prefilter: only points inside dst's bbox grown by 3 mm
        lo, hi = dst.bounds[0] - 3, dst.bounds[1] + 3
        pts = pts[np.all((pts >= lo) & (pts <= hi), axis=1)]
        if len(pts) == 0:
            continue
        _, d, _ = trimesh.proximity.closest_point(dst, pts)
        best = min(best, float(d.min()))
    return best


def run(variant):
    meshes = load_set(variant)
    lines = [f'=== variant: {variant} ===', f'parts: {", ".join(meshes)}', '']
    for n, m in meshes.items():
        if not m.is_watertight:
            lines.append(f'WARNING: {n} mesh is not watertight')
    mans = {n: to_manifold(m) for n, m in meshes.items()}
    lines.append('-- overlaps (intersection volume, mm^3) --')
    n_bad = 0
    for a, b in itertools.combinations(meshes, 2):
        ba, bb = meshes[a].bounds, meshes[b].bounds
        if np.any(ba[1] < bb[0]) or np.any(bb[1] < ba[0]):
            continue
        v = (mans[a] ^ mans[b]).volume()
        if v > 1e-3:
            n_bad += 1
            lines.append(f'OVERLAP {a} x {b}: {v:.3f} mm^3')
    if not n_bad:
        lines.append('none (all pairs < 0.001 mm^3)')
    lines.append('')
    lines.append(f'-- rotating vs stationary clearance (warn below {WARN_GAP} mm) --')
    for r in ROTATING:
        for s in meshes:
            if s in ROTATING:
                continue
            ba, bb = meshes[r].bounds, meshes[s].bounds
            if np.any(ba[1] + WARN_GAP + 1 < bb[0]) or np.any(bb[1] + WARN_GAP + 1 < ba[0]):
                continue
            d = min_distance(meshes[r], meshes[s])
            if d < WARN_GAP + 0.4:
                tag = 'OK ' if d >= WARN_GAP - 0.05 else 'LOW'
                note = KNOWN.get(frozenset((r, s)), '')
                lines.append(f'{tag} {r:24s} <-> {s:24s} min gap {d:.2f} mm  {note}')
    lines.append('')
    return lines, n_bad


def main():
    variants = sys.argv[1:] or ['classic', 'classic_pro']
    allines, bad = [], 0
    for v in variants:
        ls, nb = run(v)
        allines += ls
        bad += nb
        print('\n'.join(ls), flush=True)
    (OUT / 'check_report.txt').write_text('\n'.join(allines) + '\n')
    sys.exit(1 if bad else 0)


if __name__ == '__main__':
    main()
