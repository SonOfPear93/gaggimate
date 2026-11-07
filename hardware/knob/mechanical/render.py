#!/usr/bin/env python3
"""PNG renders of the parts and the assembly (run build.py first).

  out/renders/part_*.png            each printed part, two views
  out/renders/assembly_*.png        assembled + exploded views
  out/renders/section_3d_*.png      3D half-section through the centre
  out/renders/section_2d_*.png      2D cross-sections (filled, labelled)
"""
import sys
from pathlib import Path

import matplotlib
import numpy as np
import pyvista as pv
import trimesh

matplotlib.use('Agg')
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from shapely.geometry import Polygon  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from knobcad import params as P  # noqa: E402

pv.OFF_SCREEN = True
HERE = Path(__file__).resolve().parent
OUT = HERE / 'out'
REN = OUT / 'renders'

COL = {
    'knob_ring': '#d9822b', 'screen_platform': '#3c9d5d', 'mount_base': '#5b8bd6',
    'front_case': '#b8c0c8', 'back_case': '#8f979f', 'rotor_spacer_smartknob': '#c9b037',
    'board_a': '#2f7d32', 'board_b': '#1b5e20', 'board_c': '#43a047', 'panel': '#202020',
    'motor_stator': '#8d6e63', 'motor_rotor': '#b0bec5', 'machine_sheet': '#d0d4d8',
    'wire_bundle': '#e53935',
}
LABEL = {
    'knob_ring': 'knob ring', 'screen_platform': 'screen platform', 'mount_base': 'MountBase (SK, mod.)',
    'front_case': 'front case', 'back_case': 'back case', 'rotor_spacer_smartknob': 'RotorSpacer (SK)',
    'board_a': 'board A', 'board_b': 'board B', 'board_c': 'board C', 'panel': 'AMOLED panel',
    'motor_stator': 'motor stator (stand-in)', 'motor_rotor': 'motor rotor (stand-in)',
    'machine_sheet': 'machine front panel (stand-in, 1 mm)',
    'wire_bundle': 'wire bundle envelope',
}
# exploded offsets (mm along z)
EXPLODE = {
    'knob_ring': 70, 'panel': 110, 'board_c': 95, 'screen_platform': 85, 'rotor_spacer_smartknob': 55,
    'motor_rotor': 40, 'motor_stator': 35, 'mount_base': 25, 'front_case': 15, 'board_a': 0,
    'board_b': -25, 'back_case': -45, 'wire_bundle': 5,
}


def load(name, variant='classic'):
    if name == 'back_case':
        return OUT / 'stl' / f'back_case_{variant}.stl'
    if name == 'machine_sheet':
        return OUT / 'standins' / f'machine_sheet_{variant}.stl'
    for d in ('stl', 'standins'):
        f = OUT / d / f'{name}.stl'
        if f.exists():
            return f
    raise FileNotFoundError(name)


def assembly(variant='classic', sheet=False, wires=False):
    skip = set() if sheet else {'machine_sheet'}
    if not wires:
        skip.add('wire_bundle')
    return {n: pv.read(str(load(n, variant))) for n in COL if n not in skip}


def cam(p, view, dist=260):
    views = {
        'iso_front': ((1.0, -1.3, 1.4), (0, 0, 1)),
        'iso_back': ((-1.0, 1.3, -1.2), (0, 0, 1)),
        'front': ((0, 0, 1), (0, -1, 0)),
        'side': ((1, 0, 0.0001), (0, 0, 1)),
        'side_y': ((0.0001, 1, 0), (0, 0, 1)),
        'mounted': ((0.15, -0.55, 1.0), (0, -1, 0.35)),
    }
    d, up = views[view]
    d = np.array(d, float)
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(d * dist), (0, 0, 0), up]
    p.reset_camera()


def part_renders():
    for f in sorted((OUT / 'stl').glob('*.stl')):
        name = f.stem
        base = 'back_case' if name.startswith('back_case') else name
        m = pv.read(str(f))
        p = pv.Plotter(shape=(1, 2), window_size=(1600, 800), off_screen=True, lighting='three lights')
        for i, v in enumerate(('iso_front', 'iso_back')):
            p.subplot(0, i)
            p.add_mesh(m, color=COL[base], smooth_shading=True, split_sharp_edges=True)
            p.add_text(f'{name}  ({v.replace("_", " ")})', font_size=11)
            cam(p, v)
        p.screenshot(str(REN / f'part_{name}.png'))
        p.close()


def assembly_renders(variant):
    meshes = assembly(variant)
    for exploded in (False, True):
        p = pv.Plotter(window_size=(1400, 1400) if not exploded else (1100, 1600), off_screen=True,
                       lighting='three lights')
        for n, m in meshes.items():
            mm = m.translate((0, 0, EXPLODE[n]), inplace=False) if exploded else m
            op = 0.35 if (n in ('front_case', 'back_case') and not exploded) else 1.0
            p.add_mesh(mm, color=COL[n], smooth_shading=True, split_sharp_edges=True, opacity=op)
        p.add_text(f'GaggiMate knob, {variant.replace("_", " ")}' + (' (exploded)' if exploded else ''),
                   font_size=12)
        if exploded:
            cam(p, 'side')
            p.camera.elevation = 18
            p.camera.azimuth = -30
            p.reset_camera()
            p.camera.zoom(1.5)
        else:
            cam(p, 'iso_front')
        p.screenshot(str(REN / f'assembly_{"exploded_" if exploded else ""}{variant}.png'))
        p.close()
    # solid, as it sits on the machine (world up = u, forward = n, see params.py)
    meshes = assembly(variant, sheet=True)
    p = pv.Plotter(window_size=(1400, 1100), off_screen=True, lighting='three lights')
    for n, m in meshes.items():
        p.add_mesh(m, color=COL[n], smooth_shading=True, split_sharp_edges=True,
                   opacity=0.55 if n == 'machine_sheet' else 1.0)
    u = np.array((0, -0.919, 0.391))
    fwd = np.array((0, 0.391, 0.919))
    d = 0.75 * np.array((1, 0, 0)) + 0.8 * fwd + 0.45 * u
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(d * 300), (0, 0, -10), tuple(u)]
    p.reset_camera()
    p.camera.zoom(1.3)
    p.add_text('as mounted (screen tilted ~23 deg up)', font_size=12)
    p.screenshot(str(REN / f'assembly_{variant}.png'))
    p.close()


def section_3d(variant):
    meshes = assembly(variant, sheet=True, wires=True)
    p = pv.Plotter(window_size=(1500, 1300), off_screen=True, lighting='three lights')
    for n, m in meshes.items():
        c = m.clip(normal=(1, 0, 0), origin=(0, 0, 0))
        if c.n_points:
            p.add_mesh(c, color=COL[n], smooth_shading=False, show_edges=False)
    p.add_text(f'half section x = 0 ({variant.replace("_", " ")})', font_size=12)
    d = np.array((1.0, -0.35, 0.45))
    d /= np.linalg.norm(d)
    p.camera_position = [tuple(d * 260), (0, 0, 0), (0, 0, 1)]
    p.reset_camera()
    p.camera.zoom(1.25)
    p.screenshot(str(REN / f'section_3d_{variant}.png'))
    p.close()


def polys_from_section(mesh, normal, origin, axes):
    """Filled cross-section polygons (with holes) of a mesh."""
    s = mesh.section(plane_origin=origin, plane_normal=normal)
    if s is None:
        return []
    if tuple(normal) == (1, 0, 0):
        T = np.array([[0, 1, 0, 0], [0, 0, 1, 0], [1, 0, 0, 0], [0, 0, 0, 1]], float)
    else:
        T = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1]], float)
    import warnings
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        p2, _ = s.to_planar(to_2D=T, check=False)
    return list(p2.polygons_full)


def fill_poly(ax, poly, color):
    from matplotlib.path import Path as MPath
    from matplotlib.patches import PathPatch
    verts, codes = [], []
    for ring in [poly.exterior] + list(poly.interiors):
        c = np.asarray(ring.coords)
        verts += c.tolist()
        codes += [MPath.MOVETO] + [MPath.LINETO] * (len(c) - 2) + [MPath.CLOSEPOLY]
    ax.add_patch(PathPatch(MPath(verts, codes), fc=color, ec='k', lw=0.4, alpha=0.85))


def section_2d(variant, plane='x'):
    names = list(COL)  # includes the machine sheet stand-in
    if plane == 'x':
        normal, axes, xl = (1, 0, 0), (1, 2), 'y (case frame, +y = groove side / world down)'
    else:
        normal, axes, xl = (0, 1, 0), (0, 2), 'x (case frame)'
    fig, ax = plt.subplots(figsize=(13, 13))
    handles = []
    for n in names:
        tm = trimesh.load(load(n, variant))
        if n == 'machine_sheet':
            tm = tm.slice_plane((0, 0, -60), (0, 0, 1))
        ps = polys_from_section(tm, normal, (0, 0, 0), axes)
        for poly in ps:
            fill_poly(ax, poly, COL[n])
        if ps:
            handles.append(Patch(color=COL[n], label=LABEL[n]))
    ax.set_aspect('equal')
    ax.minorticks_on()
    ax.grid(True, lw=0.3)
    ax.grid(True, which='minor', lw=0.1)
    ax.set_xlabel(xl + ' [mm]')
    ax.set_ylabel('z [mm] (0 = top of board A, + towards user)')
    ax.legend(handles=handles, loc='lower left', fontsize=9)
    ax.set_title(f'Section {plane} = 0, {variant.replace("_", " ")} (overall depth '
                 f'{P.F - min(z for _, z in P.STOCK_PROFILES[variant]) - P.BLOCK_DZ:.1f} mm)')
    for z, t in ((P.F, 'panel / knob face'), (P.Z_CF, 'case front face'), (P.Z_J, 'case seam'),
                 (0, 'board A top'), (P.B_TOP, 'board B top'), (P.Z_FLOOR, 'back case floor')):
        ax.axhline(z, color='0.5', lw=0.4, ls='--')
        ax.text(41, z + 0.3, f'{t} ({z:.2f})', fontsize=7, color='0.3')
    ax.set_xlim(-44, 62)
    ax.set_ylim(-48, 36)
    plt.tight_layout()
    plt.savefig(REN / f'section_2d_{plane}_{variant}.png', dpi=110)
    plt.close(fig)


def detail_knob_section():
    """Close-up of the knob / platform / panel stack."""
    names = ['knob_ring', 'screen_platform', 'panel', 'board_c', 'rotor_spacer_smartknob', 'mount_base',
             'motor_rotor', 'motor_stator', 'front_case', 'board_a']
    fig, ax = plt.subplots(figsize=(14, 9))
    handles = []
    for n in names:
        tm = trimesh.load(load(n))
        ps = polys_from_section(tm, (0, 1, 0), (0, 0, 0), (0, 2))
        for poly in ps:
            fill_poly(ax, poly, COL[n])
        if ps:
            handles.append(Patch(color=COL[n], label=LABEL[n]))
    ax.set_xlim(-2, 40)
    ax.set_ylim(-2, 34)
    ax.set_aspect('equal')
    ax.minorticks_on()
    ax.grid(True, lw=0.3)
    ax.grid(True, which='minor', lw=0.1)
    ax.legend(handles=handles, loc='lower right', fontsize=9)
    ax.set_title('Detail: knob / screen stack (section y = 0, right half)')
    plt.tight_layout()
    plt.savefig(REN / 'section_2d_detail_knob.png', dpi=120)
    plt.close(fig)


def main():
    REN.mkdir(parents=True, exist_ok=True)
    part_renders()
    for v in ('classic', 'classic_pro'):
        assembly_renders(v)
        section_3d(v)
        section_2d(v, 'x')
    section_2d('classic', 'y')
    detail_knob_section()


if __name__ == '__main__':
    main()
