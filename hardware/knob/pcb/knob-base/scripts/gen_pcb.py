#!/usr/bin/env python3
"""Build knob-base.kicad_pcb (GaggiMate knob, Board A) from knob-base.kicad_sch.

Run with KiCad 10's bundled Python:
  /Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/3.9/bin/python3 scripts/gen_pcb.py

Geometry of the flexure (slots, motor holes, mount/alignment holes, MT6701 and
strain-gauge positions) is taken from SmartKnob View `electronics/view_base`
(Scott Bezek, Apache-2.0); see flexure_edges.json. The outline becomes a 75 mm
circle, everything outside the press sensor is new. Coordinates in this file
are (u, v) in mm relative to the board centre, KiCad orientation (v points
down on the front view). The board centre sits at KiCad (100, 100).

Layer use: F.Cu = front (motor / magnet side). Only U1 (MT6701) and C20 are on
the front. Everything else (strain gauges, HX711, connector) is on B.Cu, the
back side that faces Board B.
"""
from pathlib import Path
import json
import math
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

import pcbnew as pcb
import wx

sys.path.insert(0, str(Path(__file__).resolve().parent))
import router  # noqa: E402

HERE = Path(__file__).resolve().parent
PROJ = HERE.parent
NAME = 'knob-base'
BOARD = PROJ / (NAME + '.kicad_pcb')
SCH = PROJ / (NAME + '.kicad_sch')
CLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
STD = Path('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints')
LOCAL = PROJ / 'lib' / 'knob-base.pretty'
sys.path.insert(0, str(HERE))
from gen_sch import uid, ROOT  # noqa: E402

R_BOARD = 37.5
S2 = math.sqrt(0.5)


def pt(x, y):
    return pcb.VECTOR2I(pcb.FromMM(x), pcb.FromMM(y))


def G(u, v):
    return pt(100 + u, 100 + v)


def polar(r, deg):
    a = math.radians(deg)
    return (r * math.cos(a), -r * math.sin(a))


def fr(t, n):
    """Quadrant-II frame: n = radial distance along the 135 deg ray, t = tangential
    offset (positive towards 180 deg)."""
    return (-S2 * t - S2 * n, S2 * t - S2 * n)


# ------------------------------------------------------------ placement ----
# ref: (u, v, orientation_deg, side)
PLACE = {
    # --- kept from SmartKnob view_base (same coordinates) ---
    'U1': (0.0, 0.0, 180, 'F'),
    'C20': (2.0, 3.5, 180, 'F'),
    'R18': (23.5, 0.0, 180, 'B'),
    'R19': (15.6, 0.0, 180, 'B'),
    'R20': (-15.6, 0.0, 0, 'B'),
    'R21': (-23.5, 0.0, 0, 'B'),
    # --- new: connector to Board B, quadrant III, opening faces the centre ---
    'J1': (-10.0, 29.5, 0, 'B'),
}
# HX711 group in quadrant II, frame coordinates (t, n). The orientation is chosen
# automatically so that the listed pads land closest to the listed spots.
FRAME_PARTS = {
    'U4': (0.0, 22.5, {'1': (2.475, 18.055), '8': (2.475, 26.945)}),
    'Q1': (5.84, 18.85, {'2': (4.9, 17.9), '1': (4.9, 19.8)}),
    'R3': (8.6, 21.725, {'1': (8.6, 20.9)}),
    'R4': (8.6, 24.875, {'1': (8.6, 24.05)}),
    'C22': (5.4, 24.405, {'2': (4.575, 24.405)}),
    'C23': (5.0, 27.1, {'2': (5.0, 26.275)}),
    'R5': (4.5, 30.3, {'1': (4.5, 29.475)}),
    'R6': (6.2, 30.3, {'2': (6.2, 29.475)}),
    'FB1': (10.6, 21.6, {'1': (10.6, 20.54)}),
    'C18': (12.6, 23.0, {'1': (12.6, 22.05)}),
    'C19': (14.5, 23.0, {'1': (14.5, 22.2)}),
    'NT1': (0.0, 28.6, {'1': (0.0, 28.1)}),
    'C12': (-4.6, 18.6, {'1': (-4.6, 17.775)}),
    'C16': (-6.5, 18.6, {'1': (-6.5, 17.65)}),
}

HOLES = [  # ref, footprint, (u, v), value
    ('H1', 'MountingHole_M1.6', polar(10.25, -60), 'M1.6 motor'),
    ('H2', 'MountingHole_M1.6', polar(10.25, 180), 'M1.6 motor'),
    ('H3', 'MountingHole_M1.6', polar(10.25, 60), 'M1.6 motor'),
    ('H4', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (0.0, 29.8), 'M2 mount'),
    ('H5', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (-29.8, 0.0), 'M2 mount'),
    ('H6', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (0.0, -29.8), 'M2 mount'),
    ('H7', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (29.8, 0.0), 'M2 mount'),
    ('H8', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (35.0, 0.0), 'D2.2 align'),
    ('H9', 'MountingHole_2.2mm_M2_ISO7380_Pad_NonVirtual', (-35.0, 0.0), 'D2.2 align'),
]
SLOT = {'r': 33.5, 'deg': 225.0, 'w': 3.0, 'l': 7.0}

W = 0.25
# Hand routes inside the flexure (inner disc + arms). Strain-gauge topology follows
# SmartKnob view_base (bridge nets leave via the +X->90deg and -X arms on B.Cu);
# geometry redrawn for 0.25 mm tracks / 0.15 mm clearance / 0.3 mm edge clearance.
# Encoder nets leave via the 270deg arm on F.Cu (SmartKnob used the -X arm).
HAND = [
    # net, layer, width, points (pad refs 'REF.PAD' or (u, v))
    ('BRIDGE_S+', 'B', W, ['R18.2', 'R19.1']),
    ('BRIDGE_S+', 'B', W, ['R19.1', (18.562, -2.0), (13.6, -2.0), (13.6, -4.4), (12.6, -5.4), (3.5, -5.4),
                          (0.6, -8.3), (0.6, -24.9)]),
    ('GNDA', 'B', W, ['R19.2', (12.638, -4.5), (2.0, -4.5), (-0.6, -7.1), (-0.6, -24.9)]),
    ('BRIDGE_S-', 'B', W, ['R20.1', 'R21.2']),
    ('BRIDGE_S-', 'B', W, ['R21.2', (-20.537, -2.0), (-24.6, -2.0), (-24.6, -4.3)]),
    ('BRIDGE_E+', 'B', W, ['R20.2', (-12.638, -2.45)]),
    ('BRIDGE_E+', 'F', W, [(-12.638, -2.45), (-13.888, -1.2), (-25.0, -1.2)]),
    # encoder: front side, down the 270 deg arm
    ('+3V3', 'F', W, ['U1.2', 'U1.1', 'C20.1', (2.775, 5.0), (1.5, 6.275), (1.5, 24.9)]),
    ('ENC_CS', 'F', W, ['U1.8', (-0.3, 1.905), (0.5, 2.705), (0.5, 24.9)]),
    ('ENC_CLK', 'F', W, ['U1.7', (-3.9, 0.635), (-3.9, 3.1), (-0.5, 6.5), (-0.5, 24.9)]),
    ('ENC_DO', 'F', W, ['U1.6', (-4.7, -0.635), (-4.7, 3.7), (-1.5, 6.9), (-1.5, 24.9)]),
    ('GND', 'F', W, ['U1.4', (4.0, -1.905)]),
    ('GND', 'F', W, ['C20.2', (1.225, 4.6)]),
    ('GND', 'B', W, [(4.0, -1.905), (4.0, 4.0), (1.5, 6.5), (1.5, 24.9)]),
    ('GND', 'B', W, [(1.225, 4.6), (3.0, 5.0)]),
]
HAND_VIAS = [('BRIDGE_E+', (-12.638, -2.45)), ('GND', (4.0, -1.905)), ('GND', (1.225, 4.6))]
# auto-route order (nets not listed are routed afterwards)
ORDER = ['HX_BASE', 'HX_VFB', 'HX_VBG', 'HX_INA-', 'HX_INA+', 'HX_AVDD', 'GNDA', 'BRIDGE_S-', 'BRIDGE_S+',
         'BRIDGE_E+', 'HX_SCK', 'HX_DOUT', 'ENC_CS', 'ENC_CLK', 'ENC_DO', '+3V3', 'GND']


def keepout(u, v):
    """Region reserved for the hand routes: inner disc, arc slots and the four arms."""
    if u * u + v * v < 16.3 ** 2:
        return True
    # M2 screw head / nut (both sides) and alignment-pin keep-outs
    for hu, hv, hr in ((0, 29.8, 2.7), (-29.8, 0, 2.7), (0, -29.8, 2.7), (29.8, 0, 2.7), (35, 0, 2.7), (-35, 0, 2.7)):
        if (u - hu) ** 2 + (v - hv) ** 2 < hr * hr:
            return True
    for au, av in ((1, 0), (0, -1), (-1, 0), (0, 1)):
        along = u * au + v * av
        perp = abs(u * av - v * au)
        if 0 < along < 24.7 and perp < 3.9:
            return True
    return False


def load_fp(fpid):
    lib, name = fpid.split(':')
    d = LOCAL if lib == 'knob-base' else STD / (lib + '.pretty')
    f = pcb.FootprintLoad(str(d), name)
    assert f, fpid
    f.SetFPIDAsString(fpid)
    return f


def netlist():
    with tempfile.TemporaryDirectory() as tmp:
        x = Path(tmp) / 'n.xml'
        subprocess.run([CLI, 'sch', 'export', 'netlist', str(SCH), '--format', 'kicadxml', '--output', str(x)],
                       check=True, capture_output=True)
        return ET.parse(x).getroot()


def build(plan_only=False):
    root = netlist()
    board = pcb.BOARD()
    board.SetFileName(str(BOARD))
    board.SetCopperLayerCount(2)
    ds = board.GetDesignSettings()
    ds.SetBoardThickness(pcb.FromMM(1.2))
    nets = {}
    pin_net = {}
    for n in root.findall('./nets/net'):
        name = n.get('name')
        ni = pcb.NETINFO_ITEM(board, name)
        board.Add(ni)
        nets[name] = ni
        for node in n.findall('node'):
            pin_net[(node.get('ref'), node.get('pin'))] = ni

    def netcode(name):
        for k in (name, '/' + name):
            if k in nets:
                return nets[k].GetNetCode()
        raise KeyError(name)

    fps = {}
    for c in root.findall('./components/comp'):
        ref = c.get('ref')
        f = load_fp(c.findtext('footprint'))
        f.SetReference(ref)
        f.SetValue(c.findtext('value'))
        f.SetPath(pcb.KIID_PATH('/' + uid('sym-' + ref)))
        f.SetSheetfile(NAME + '.kicad_sch')
        f.SetSheetname('/')
        for fld in c.findall('./fields/field'):
            if fld.get('name') in ('Footprint', 'Datasheet', 'Description'):
                continue
            f.SetField(fld.get('name'), fld.text or '')
            f.GetField(fld.get('name')).SetVisible(False)
        if ref.startswith('NT'):
            f.SetExcludedFromBOM(True)
            f.SetExcludedFromPosFiles(True)
        for p in f.Pads():
            ni = pin_net.get((ref, p.GetNumber()))
            if ni is not None:
                p.SetNet(ni)
        board.Add(f)
        fps[ref] = f
    for ref, name, (u, v), value in HOLES:
        h = load_fp('knob-base:' + name)
        h.SetReference(ref)
        h.SetValue(value)
        h.SetBoardOnly(True)
        h.SetExcludedFromBOM(True)
        h.SetExcludedFromPosFiles(True)
        h.SetPosition(G(u, v))
        h.Reference().SetVisible(False)
        board.Add(h)
        fps[ref] = h

    # placement
    def put(ref, u, v, rot, side):
        f = fps[ref]
        f.SetPosition(G(u, v))
        if side == 'B' and not f.IsFlipped():
            f.Flip(G(u, v), pcb.FLIP_DIRECTION_TOP_BOTTOM)
        f.SetOrientationDegrees(rot)

    for ref, (u, v, rot, side) in PLACE.items():
        put(ref, u, v, rot, side)
    def frame_of(p):
        u, v = pcb.ToMM(p.x) - 100, pcb.ToMM(p.y) - 100
        return (-S2 * u + S2 * v, -S2 * u - S2 * v)

    for ref, (t_, n_, want) in FRAME_PARTS.items():
        u, v = fr(t_, n_)
        best = None
        for rot in range(0, 360, 45):
            put(ref, u, v, rot, 'B')
            err = 0.0
            for num, (wt, wn) in want.items():
                pp = [p for p in fps[ref].Pads() if p.GetNumber() == num][0].GetPosition()
                ft, fn = frame_of(pp)
                err += (ft - wt) ** 2 + (fn - wn) ** 2
            if best is None or err < best[0] - 1e-9:
                best = (err, rot)
        put(ref, u, v, best[1], 'B')
        assert best[0] < 0.05, (ref, best)
    unplaced = [r for r in fps if r not in PLACE and r not in FRAME_PARTS and not r.startswith('H')]
    assert not unplaced, unplaced
    # reference designators: only where they fit on a part body, others live on the Fab layers
    for ref, f in fps.items():
        if ref.startswith('H'):
            continue
        rt = f.Reference()
        rt.SetTextSize(pt(0.8, 0.8))
        rt.SetTextThickness(pcb.FromMM(0.12))
        f.Value().SetVisible(False)
        if ref in ('U1', 'U4', 'R18', 'R19', 'R20', 'R21'):
            rt.SetPosition(f.GetPosition())
            rt.SetTextAngleDegrees(0)
            rt.SetVisible(True)
        elif ref == 'J1':
            rt.SetPosition(G(-10.0, 25.6))
            rt.SetTextAngleDegrees(0)
            rt.SetVisible(True)
        else:
            rt.SetVisible(False)

    # outline
    def shape(kind):
        s = pcb.PCB_SHAPE(board)
        s.SetShape(kind)
        s.SetLayer(pcb.Edge_Cuts)
        s.SetWidth(pcb.FromMM(0.1))
        board.Add(s)
        return s

    c = shape(pcb.SHAPE_T_CIRCLE)
    c.SetCenter(G(0, 0))
    c.SetEnd(G(R_BOARD, 0))
    for it in json.loads((HERE / 'flexure_edges.json').read_text())['items']:
        if it['type'] == 'line':
            s = shape(pcb.SHAPE_T_SEGMENT)
            s.SetStart(G(*it['start']))
            s.SetEnd(G(*it['end']))
        elif it['type'] == 'arc':
            s = shape(pcb.SHAPE_T_ARC)
            s.SetArcGeometry(G(*it['start']), G(*it['mid']), G(*it['end']))
        else:
            s = shape(pcb.SHAPE_T_CIRCLE)
            s.SetCenter(G(*it['center']))
            s.SetEnd(G(it['center'][0] + it['radius'], it['center'][1]))
    # wire pass-through slot, long axis tangential
    cu, cv = polar(SLOT['r'], SLOT['deg'])
    a = math.radians(SLOT['deg'])
    tu, tv = -math.sin(a), -math.cos(a)        # tangent (screen coords)
    ru, rv = math.cos(a), -math.sin(a)         # radial
    h, rr = (SLOT['l'] - SLOT['w']) / 2, SLOT['w'] / 2
    e1 = (cu + tu * h, cv + tv * h)
    e2 = (cu - tu * h, cv - tv * h)
    for sgn in (1, -1):
        s = shape(pcb.SHAPE_T_SEGMENT)
        s.SetStart(G(e1[0] + sgn * ru * rr, e1[1] + sgn * rv * rr))
        s.SetEnd(G(e2[0] + sgn * ru * rr, e2[1] + sgn * rv * rr))
    for e, sg in ((e1, 1), (e2, -1)):
        s = shape(pcb.SHAPE_T_ARC)
        s.SetArcGeometry(G(e[0] + ru * rr, e[1] + rv * rr), G(e[0] + sg * tu * rr, e[1] + sg * tv * rr),
                         G(e[0] - ru * rr, e[1] - rv * rr))

    # copper
    def padpos(spec):
        ref, num = spec.split('.')
        p = [p for p in fps[ref].Pads() if p.GetNumber() == num][0].GetPosition()
        return (pcb.ToMM(p.x) - 100, pcb.ToMM(p.y) - 100)

    def resolve(p):
        if isinstance(p, str):
            return padpos(p)
        if p[0] == 'F':
            return fr(p[1], p[2])
        return p

    def add_track(net, layer, width, a_, b_):
        tr = pcb.PCB_TRACK(board)
        tr.SetStart(G(*a_))
        tr.SetEnd(G(*b_))
        tr.SetWidth(pcb.FromMM(width))
        tr.SetLayer(pcb.F_Cu if layer in ('F', 0) else pcb.B_Cu)
        tr.SetNetCode(netcode(net))
        board.Add(tr)

    def add_via(net, p):
        vv = pcb.PCB_VIA(board)
        vv.SetPosition(G(*p))
        vv.SetWidth(pcb.FromMM(router.VIA_D))
        vv.SetDrill(pcb.FromMM(router.VIA_DRILL))
        vv.SetViaType(pcb.VIATYPE_THROUGH)
        vv.SetLayerPair(pcb.F_Cu, pcb.B_Cu)
        vv.SetNetCode(netcode(net))
        board.Add(vv)

    for net, layer, width, pts in HAND:
        P = [resolve(p) for p in pts]
        for a_, b_ in zip(P, P[1:]):
            add_track(net, layer, width, a_, b_)
    for net, p in HAND_VIAS:
        add_via(net, p)
    if plan_only:
        return board, fps, []

    # ---- auto-route everything else on the outer body ----
    R = router.Router(board, width=W, keepout=keepout)
    code_name = {}
    for name, ni in nets.items():
        code_name[ni.GetNetCode()] = name.lstrip('/')
    pad_cells = {}
    for ref, f in fps.items():
        for gi in f.GraphicalItems():
            for lid, L in ((pcb.F_Cu, 0), (pcb.B_Cu, 1)):
                if gi.IsOnLayer(lid):
                    poly = pcb.SHAPE_POLY_SET()
                    gi.TransformShapeToPolygon(poly, lid, pcb.FromMM(router.CLR + router.VIA_D / 2 + 0.25), pcb.FromMM(0.005), pcb.ERROR_OUTSIDE)
                    R.mark_novia(poly)
    for ref, f in fps.items():
        for p in f.Pads():
            R.add_pad(p)
            if p.GetNetCode() > 0:
                poly = pcb.SHAPE_POLY_SET()
                lid = pcb.F_Cu if p.IsOnLayer(pcb.F_Cu) else pcb.B_Cu
                p.TransformShapeToPolygon(poly, lid, 0, pcb.FromMM(0.005), pcb.ERROR_INSIDE)
                cells = set()
                layers = [L for L, lid_ in ((0, pcb.F_Cu), (1, pcb.B_Cu)) if p.IsOnLayer(lid_)]
                bb = poly.BBox()
                for j in range(int((pcb.ToMM(bb.GetTop()) - 100 + router.HALF) / router.G),
                               int((pcb.ToMM(bb.GetBottom()) - 100 + router.HALF) / router.G) + 2):
                    for i in range(int((pcb.ToMM(bb.GetLeft()) - 100 + router.HALF) / router.G),
                                   int((pcb.ToMM(bb.GetRight()) - 100 + router.HALF) / router.G) + 2):
                        u, v = -router.HALF + i * router.G, -router.HALF + j * router.G
                        if poly.Contains(pt(100 + u, 100 + v)):
                            for L in layers:
                                cells.add((L, j * router.N + i))
                pad_cells[(ref, p.GetNumber())] = (p.GetNetCode(), cells)
    # islands: pads joined by hand routes
    parent = {}

    def find(x):
        while parent.get(x, x) != x:
            x = parent[x]
        return x

    island_cells = {}
    for key, (nc, cells) in pad_cells.items():
        island_cells.setdefault(key, set()).update(cells)
    for net, layer, width, pts in HAND:
        L = 0 if layer == 'F' else 1
        P = [resolve(p) for p in pts]
        pads_in = [tuple(p.split('.')) for p in pts if isinstance(p, str)]
        key = pads_in[0] if pads_in else ('hand', net, P[0])
        # chains that start at a free point join the chain that ends there
        if not pads_in:
            for k2 in list(island_cells):
                if any(router.cell(*P[0]) == c for (_, c) in island_cells[k2]):
                    key = k2
                    break
        cells = island_cells.setdefault(key, set())
        for a_, b_ in zip(P, P[1:]):
            R.add_track(L, a_, b_, netcode(net), width)
            d = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
            for k in range(int(d / 0.05) + 1):
                tt = k / max(1, int(d / 0.05))
                c = router.cell(a_[0] + tt * (b_[0] - a_[0]), a_[1] + tt * (b_[1] - a_[1]))
                cells.add((L, c))
        for other in pads_in[1:]:
            parent[find(other)] = find(key)
    for net, p in HAND_VIAS:
        R.add_via(p, netcode(net))
        c = router.cell(*p)
        for k in list(island_cells):
            if (0, c) in island_cells[k] or (1, c) in island_cells[k]:
                island_cells[k].update({(0, c), (1, c)})
    # merge islands sharing cells (hand chains continuing from a via)
    keys = list(island_cells)
    for i in range(len(keys)):
        for j in range(i + 1, len(keys)):
            a_, b_ = keys[i], keys[j]
            na = pad_cells.get(a_, (None,))[0]
            if find(a_) != find(b_) and island_cells[a_] & island_cells[b_]:
                parent[find(b_)] = find(a_)
    groups = {}
    for k, cells in island_cells.items():
        r_ = find(k)
        groups.setdefault(r_, set()).update(cells)
    net_of_group = {}
    for k in island_cells:
        if k in pad_cells:
            net_of_group[find(k)] = pad_cells[k][0]
        elif k[0] == 'hand':
            net_of_group.setdefault(find(k), netcode(k[1]))
    by_net = {}
    for g_, cells in groups.items():
        by_net.setdefault(net_of_group[g_], []).append(cells)

    order = [netcode(n) for n in ORDER] + [c for c in by_net if c not in [netcode(n) for n in ORDER]]
    failures = []
    routed = []
    for nc in order:
        isl = by_net.get(nc, [])
        if len(isl) < 2:
            continue
        tree = set(isl[0])
        rest = [set(s) for s in isl[1:]]
        while rest:
            targets = set().union(*rest)
            path = R.astar(nc, tree, targets)
            if path is None:
                failures.append((code_name[nc], len(rest)))
                break
            end = path[-1]
            hit = [s for s in rest if end in s][0]
            rest.remove(hit)
            tree |= hit
            for L, pts_ in R.simplify(path, nc):
                for a_, b_ in zip(pts_, pts_[1:]):
                    add_track(code_name[nc], L, W, a_, b_)
                    R.add_track(L, a_, b_, nc, W)
                    routed.append((code_name[nc], L, a_, b_))
                    d = math.hypot(b_[0] - a_[0], b_[1] - a_[1])
                    nn = max(1, int(d / 0.03))
                    for k in range(nn + 1):
                        tree.add((L, router.cell(a_[0] + k / nn * (b_[0] - a_[0]), a_[1] + k / nn * (b_[1] - a_[1]))))
            for s0, s1 in zip(path, path[1:]):
                if s0[0] != s1[0]:
                    p_ = router.uv(s0[1])
                    add_via(code_name[nc], p_)
                    R.add_via(p_, nc)
                    tree |= {(0, s0[1]), (1, s0[1])}
        print('routed', code_name[nc], flush=True)
    return board, fps, failures
    return board, fps


def plan_svg(board, fps, path, box=(-40, -40, 80, 80)):
    """Debug drawing: pads coloured by layer with net names, tracks, edges."""
    sc = 12
    x0, y0, w0, h0 = box
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{x0*sc} {y0*sc} {w0*sc} {h0*sc}" '
           f'width="{w0*sc}" height="{h0*sc}">', f'<rect x="{x0*sc}" y="{y0*sc}" width="{w0*sc}" height="{h0*sc}" fill="#fff"/>']
    X = lambda x: (pcb.ToMM(x) - 100) * sc
    for d in board.GetDrawings():
        if d.GetLayer() != pcb.Edge_Cuts:
            continue
        if d.GetShape() == pcb.SHAPE_T_CIRCLE:
            out.append(f'<circle cx="{X(d.GetCenter().x)}" cy="{X(d.GetCenter().y)}" r="{pcb.ToMM(d.GetRadius())*sc}" fill="none" stroke="#000" stroke-width="1.5"/>')
        elif d.GetShape() == pcb.SHAPE_T_SEGMENT:
            out.append(f'<line x1="{X(d.GetStart().x)}" y1="{X(d.GetStart().y)}" x2="{X(d.GetEnd().x)}" y2="{X(d.GetEnd().y)}" stroke="#000" stroke-width="1.5"/>')
        else:
            pts = [d.GetStart(), d.GetArcMid(), d.GetEnd()]
            out.append('<polyline fill="none" stroke="#000" stroke-width="1.5" points="' + ' '.join(f'{X(p.x)},{X(p.y)}' for p in pts) + '"/>')
    for t in board.GetTracks():
        if t.Type() == pcb.PCB_VIA_T:
            out.append(f'<circle cx="{X(t.GetPosition().x)}" cy="{X(t.GetPosition().y)}" r="{0.3*sc}" fill="#080"/>')
        else:
            col = '#d33' if t.GetLayer() == pcb.F_Cu else '#33d'
            out.append(f'<line x1="{X(t.GetStart().x)}" y1="{X(t.GetStart().y)}" x2="{X(t.GetEnd().x)}" y2="{X(t.GetEnd().y)}" stroke="{col}" stroke-opacity="0.6" stroke-width="{pcb.ToMM(t.GetWidth())*sc}" stroke-linecap="round"/>')
    for ref, f in fps.items():
        for p in f.Pads():
            poly = p.GetEffectivePolygon(pcb.F_Cu if not f.IsFlipped() else pcb.B_Cu, pcb.ERROR_INSIDE)
            o = poly.Outline(0)
            col = '#f99' if not f.IsFlipped() else '#99f'
            if p.GetAttribute() == pcb.PAD_ATTRIB_PTH:
                col = '#bbb'
            out.append(f'<polygon fill="{col}" fill-opacity="0.7" points="' + ' '.join(f'{X(o.CPoint(i).x)},{X(o.CPoint(i).y)}' for i in range(o.PointCount())) + '"/>')
            c = p.GetPosition()
            lab = f'{ref}.{p.GetNumber()} {p.GetNetname().lstrip("/")}' if not ref.startswith('H') else ref
            out.append(f'<text x="{X(c.x)}" y="{X(c.y)}" font-size="5" font-family="Helvetica" text-anchor="middle">{lab}</text>')
    for r in range(16, 38, 2):
        out.append(f'<circle cx="0" cy="0" r="{r*sc}" fill="none" stroke="#ccc" stroke-width="0.4"/>')
    out.append('</svg>')
    Path(path).write_text('\n'.join(out))


RULES = {'min_clearance': 0.15, 'min_track_width': 0.15, 'min_via_diameter': 0.5, 'min_via_annular_width': 0.1,
         'min_through_hole_diameter': 0.3, 'min_hole_clearance': 0.25, 'min_hole_to_hole': 0.25,
         'min_copper_edge_clearance': 0.3, 'min_silk_clearance': 0.0, 'min_text_height': 0.8,
         'min_text_thickness': 0.12, 'solder_mask_to_copper_clearance': 0.0}


def text(board, s, u, v, layer, size=1.0, angle=0.0, mirror=False):
    t_ = pcb.PCB_TEXT(board)
    t_.SetText(s)
    t_.SetPosition(G(u, v))
    t_.SetLayer(layer)
    t_.SetTextSize(pt(size, size))
    t_.SetTextThickness(pcb.FromMM(0.15 if size >= 1 else 0.12))
    t_.SetTextAngleDegrees(angle)
    if mirror:
        t_.SetMirrored(True)
    board.Add(t_)


def finish(board):
    ds = board.GetDesignSettings()
    ds.m_MinClearance = pcb.FromMM(0.15)
    ds.m_TrackMinWidth = pcb.FromMM(0.15)
    ds.m_CopperEdgeClearance = pcb.FromMM(0.3)
    gnd = board.FindNet('GND')
    for layer in (pcb.F_Cu, pcb.B_Cu):
        z = pcb.ZONE(board)
        z.SetLayer(layer)
        z.SetNetCode(gnd.GetNetCode())
        z.SetLocalClearance(pcb.FromMM(0.25))
        z.SetMinThickness(pcb.FromMM(0.2))
        z.SetPadConnection(pcb.ZONE_CONNECTION_THERMAL)
        z.SetThermalReliefGap(pcb.FromMM(0.25))
        z.SetThermalReliefSpokeWidth(pcb.FromMM(0.3))
        z.SetIslandRemovalMode(pcb.ISLAND_REMOVAL_MODE_ALWAYS)
        ol = z.Outline()
        ol.NewOutline()
        for k in range(180):
            a = 2 * math.pi * k / 180
            ol.Append(G(37.4 * math.cos(a), 37.4 * math.sin(a)))
        board.Add(z)
    # silkscreen: back side (assembly side facing Board B) carries the notes
    for k, (s, sz) in enumerate([('GaggiMate knob', 1.0), ('Board A "knob-base" rev 1', 0.8), ('2026-11-07', 0.8),
                                 ('flexure, MT6701, HX711 circuit:', 0.8), ('SmartKnob View by Scott Bezek', 0.8),
                                 ('(Apache-2.0)', 0.8)]):
        text(board, s, 17.5, -24.0 + k * 1.45, pcb.B_SilkS, sz, mirror=True)
    for k, s in enumerate(['J1 to Board B (JST-SH 8p)', '1 3V3   2 GND', '3 ENC_CS   4 ENC_CLK', '5 ENC_DO   6 HX_SCK',
                           '7 HX_DOUT   8 GND']):
        text(board, s, -12.0, 16.5 + k * 1.3, pcb.B_SilkS, 0.8, mirror=True)
    text(board, 'WIRES', *polar(29.6, 225), pcb.F_SilkS, 0.8, angle=45)
    text(board, 'WIRES', *polar(29.6, 225), pcb.B_SilkS, 0.8, angle=-45, mirror=True)
    text(board, 'knob-base r1 (front)', 17.0, -21.0, pcb.F_SilkS, 0.8)
    board.BuildConnectivity()
    filler = pcb.ZONE_FILLER(board)
    filler.Fill(board.Zones())
    pcb.SaveBoard(str(BOARD), board)
    pro = BOARD.with_suffix('.kicad_pro')
    st = json.loads(pro.read_text())
    st.setdefault('board', {}).setdefault('design_settings', {}).setdefault('rules', {}).update(RULES)
    dset = st['board']['design_settings']
    dset.setdefault('defaults', {})
    ns = st.setdefault('net_settings', {})
    cls = ns.get('classes') or [{}]
    cls[0].update({'name': 'Default', 'clearance': 0.15, 'track_width': 0.25, 'via_diameter': 0.6,
                   'via_drill': 0.3, 'microvia_diameter': 0.3, 'microvia_drill': 0.1})
    ns['classes'] = cls
    st.setdefault('meta', {})['filename'] = NAME + '.kicad_pro'
    pro.write_text(json.dumps(st, indent=2) + '\n')
    print('saved', BOARD)


if __name__ == '__main__':
    app = wx.App(False)
    mode = sys.argv[1] if len(sys.argv) > 1 else 'build'
    b, f, fail = build(plan_only=(mode == 'plan'))
    if len(sys.argv) > 2:
        plan_svg(b, f, sys.argv[2])
        plan_svg(b, f, sys.argv[2].replace('.svg', '_q2.svg'), (-32, -32, 26, 26))
    print('FAILURES', fail)
    if mode == 'build':
        finish(b)
