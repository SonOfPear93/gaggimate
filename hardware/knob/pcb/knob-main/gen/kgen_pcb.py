"""PCB building helpers (run with KiCad's bundled python, needs pcbnew)."""
import os, sys, math, subprocess
import pcbnew
from sexp import parse, find, find1

FPDIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
KCLI = '/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli'
MM = pcbnew.FromMM


def P(x, y):
    return pcbnew.VECTOR2I(MM(x), MM(y))


def read_netlist(path):
    d = parse(open(path).read())[0]
    comps = {}
    for c in find(find1(d, 'components'), 'comp'):
        ref = find1(c, 'ref')[1]
        fields = {}
        fl = find1(c, 'fields')
        if fl:
            for f in find(fl, 'field'):
                fields[find1(f, 'name')[1]] = f[2] if len(f) > 2 and not isinstance(f[2], list) else ''
        props = {p[1][1] if isinstance(p[1], list) else find1(p, 'name')[1]: (find1(p, 'value')[1] if find1(p, 'value') else '')
                 for p in find(c, 'property')}
        ts = find1(c, 'tstamps') or find1(c, 'tstamp')
        sp = find1(c, 'sheetpath')
        comps[ref] = dict(ref=ref, value=find1(c, 'value')[1], footprint=find1(c, 'footprint')[1] if find1(c, 'footprint') else '',
                          fields=fields, props=props, tstamp=ts[1], sheet_tstamps=find1(sp, 'tstamps')[1])
    nets = {}
    for n in find(find1(d, 'nets'), 'net'):
        name = find1(n, 'name')[1]
        nets[name] = [(find1(nd, 'ref')[1], find1(nd, 'pin')[1]) for nd in find(n, 'node')]
    return comps, nets


def fp_load(fpid, local_libs):
    lib, name = fpid.split(':')
    path = local_libs.get(lib, os.path.join(FPDIR, lib + '.pretty'))
    fp = pcbnew.FootprintLoad(path, name)
    if fp is None:
        raise RuntimeError('footprint not found ' + fpid)
    fp.SetFPID(pcbnew.LIB_ID(lib, name))
    return fp


def build(board_path, netlist, place, local_libs, layers=2, thickness=1.6, extra_fields=('LCSC', 'MPN', 'Description', 'Datasheet')):
    comps, nets = read_netlist(netlist)
    b = pcbnew.BOARD()
    b.SetCopperLayerCount(layers)
    ds = b.GetDesignSettings()
    ds.SetBoardThickness(MM(thickness))
    netinfo = {}
    for name in nets:
        ni = pcbnew.NETINFO_ITEM(b, name)
        b.Add(ni)
        netinfo[name] = ni
    padnet = {}
    for name, nodes in nets.items():
        for ref, pin in nodes:
            padnet[(ref, pin)] = name
    for ref, c in comps.items():
        if ref not in place:
            raise RuntimeError('no placement for ' + ref)
        x, y, rot, side = place[ref]
        fp = fp_load(c['footprint'], local_libs)
        fp.SetReference(ref)
        fp.SetValue(c['value'])
        for k in extra_fields:
            v = c['fields'].get(k) or c['props'].get(k)
            if v:
                fp.SetField(k, v)
                f = fp.GetField(k)
                f.SetVisible(False)
                f.SetLayer(pcbnew.F_Fab)
        fp.SetPath(pcbnew.KIID_PATH('/' + c['tstamp']))
        if 'exclude_from_bom' in c['props']:
            fp.SetExcludedFromBOM(True)
        if 'dnp' in c['props']:
            fp.SetDNP(True)
        b.Add(fp)
        fp.SetPosition(P(x, y))
        if side == 'B':
            fp.Flip(fp.GetPosition(), pcbnew.FLIP_DIRECTION_LEFT_RIGHT)
        fp.SetOrientationDegrees(rot)
        for pad in fp.Pads():
            n = padnet.get((ref, pad.GetNumber()))
            if n:
                pad.SetNet(netinfo[n])
    return b, comps, nets


def add_circle_outline(b, cx, cy, r, width=0.1):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_CIRCLE)
    s.SetCenter(P(cx, cy))
    s.SetEnd(P(cx + r, cy))
    s.SetLayer(pcbnew.Edge_Cuts)
    s.SetWidth(MM(width))
    b.Add(s)


def add_line(b, x1, y1, x2, y2, layer, width=0.12):
    s = pcbnew.PCB_SHAPE(b)
    s.SetShape(pcbnew.SHAPE_T_SEGMENT)
    s.SetStart(P(x1, y1)); s.SetEnd(P(x2, y2))
    s.SetLayer(layer); s.SetWidth(MM(width))
    b.Add(s)


def add_text(b, txt, x, y, layer, size=1.0, rot=0, thick=0.15, mirror=False):
    t = pcbnew.PCB_TEXT(b)
    t.SetText(txt)
    t.SetPosition(P(x, y))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(MM(size), MM(size)))
    t.SetTextThickness(MM(thick))
    t.SetTextAngleDegrees(rot)
    if mirror:
        t.SetMirrored(True)
    b.Add(t)
    return t


def add_zone(b, net, layer, pts, clearance=0.25, minw=0.2, thermal_gap=0.3, spoke=0.35, priority=0, name=None):
    z = pcbnew.ZONE(b)
    z.SetLayer(layer)
    if net is not None:
        z.SetNet(b.FindNet(net))
    ol = z.Outline()
    ol.NewOutline()
    for (x, y) in pts:
        ol.Append(MM(x), MM(y))
    z.SetLocalClearance(MM(clearance))
    z.SetMinThickness(MM(minw))
    z.SetThermalReliefGap(MM(thermal_gap))
    z.SetThermalReliefSpokeWidth(MM(spoke))
    z.SetPadConnection(pcbnew.ZONE_CONNECTION_THERMAL)
    z.SetAssignedPriority(priority)
    if name:
        z.SetZoneName(name)
    b.Add(z)
    return z


def add_keepout(b, pts, layers, tracks=True, vias=True, pads=False, pour=True, fps=False, name=None):
    z = pcbnew.ZONE(b)
    z.SetIsRuleArea(True)
    ls = pcbnew.LSET()
    for l in layers:
        ls.AddLayer(l)
    z.SetLayerSet(ls)
    ol = z.Outline(); ol.NewOutline()
    for (x, y) in pts:
        ol.Append(MM(x), MM(y))
    z.SetDoNotAllowTracks(tracks); z.SetDoNotAllowVias(vias); z.SetDoNotAllowPads(pads)
    z.SetDoNotAllowZoneFills(pour); z.SetDoNotAllowFootprints(fps)
    if name:
        z.SetZoneName(name)
    b.Add(z)
    return z


def circle_pts(cx, cy, r, n=72):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]


def add_track(b, net, layer, pts, width):
    for (x1, y1), (x2, y2) in zip(pts[:-1], pts[1:]):
        t = pcbnew.PCB_TRACK(b)
        t.SetStart(P(x1, y1)); t.SetEnd(P(x2, y2))
        t.SetWidth(MM(width)); t.SetLayer(layer)
        t.SetNet(b.FindNet(net))
        b.Add(t)


def add_via(b, net, x, y, d=0.6, drill=0.3):
    v = pcbnew.PCB_VIA(b)
    v.SetPosition(P(x, y))
    v.SetWidth(MM(d)); v.SetDrill(MM(drill))
    v.SetNet(b.FindNet(net))
    v.SetViaType(pcbnew.VIATYPE_THROUGH)
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu)
    b.Add(v)
    return v


def fill_zones(b):
    f = pcbnew.ZONE_FILLER(b)
    f.Fill(b.Zones())


GRAVE = []  # keep python refs to removed items (SWIG otherwise corrupts the board's track list)


def remove_dangling(b, iterations=10):
    """Remove track segments with an end that touches nothing (pad, via, other track) on its layer."""
    removed = 0
    seen = set()
    for t in list(b.GetTracks()):
        if t.GetClass() != 'PCB_TRACK':
            continue
        a, c = (t.GetStart().x, t.GetStart().y), (t.GetEnd().x, t.GetEnd().y)
        key = (min(a, c), max(a, c), t.GetLayer())
        if key in seen or a == c:
            b.Remove(t); GRAVE.append(t); removed += 1
        else:
            seen.add(key)
    for _ in range(iterations):
        tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
        vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
        pads = list(b.GetPads())
        ends = {}
        for t in tracks:
            for p in (t.GetStart(), t.GetEnd()):
                ends.setdefault((p.x, p.y, t.GetLayer()), []).append(t)
        kill = []
        for t in tracks:
            for p in (t.GetStart(), t.GetEnd()):
                if len(ends[(p.x, p.y, t.GetLayer())]) > 1:
                    continue
                ok = any(v.GetPosition().x == p.x and v.GetPosition().y == p.y for v in vias)
                if not ok:
                    for pad in pads:
                        if pad.IsOnLayer(t.GetLayer()) and pad.HitTest(p):
                            ok = True
                            break
                if not ok:
                    # touching the middle of another segment of the same net?
                    for o in tracks:
                        if o is not t and o.GetLayer() == t.GetLayer() and o.GetNetCode() == t.GetNetCode() and o.HitTest(p, 1):
                            ok = True
                            break
                if not ok:
                    kill.append(t)
                    break
        if not kill:
            break
        for t in kill:
            b.Remove(t)
            GRAVE.append(t)
            removed += 1
    # signal vias that only touch copper on one layer (escape vias the router did not use) + their stubs
    for v in [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']:
        if v.GetNetname() in ('/GND', '/+3V3'):
            continue
        p0 = v.GetPosition()
        layers = set()
        for t in b.GetTracks():
            if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == v.GetNetCode() and (t.GetStart() == p0 or t.GetEnd() == p0):
                layers.add(t.GetLayer())
        if len(layers) <= 1:
            b.Remove(v); GRAVE.append(v); removed += 1
    if removed:
        for _ in range(iterations):
            n0 = removed
            tracks = [t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK']
            vias = [t for t in b.GetTracks() if t.GetClass() == 'PCB_VIA']
            pads = list(b.GetPads())
            ends = {}
            for t in tracks:
                for p in (t.GetStart(), t.GetEnd()):
                    ends.setdefault((p.x, p.y, t.GetLayer()), []).append(t)
            for t in tracks:
                for p in (t.GetStart(), t.GetEnd()):
                    if len(ends[(p.x, p.y, t.GetLayer())]) > 1 or any(vv.GetPosition() == p for vv in vias):
                        continue
                    if any(pad.IsOnLayer(t.GetLayer()) and pad.HitTest(p) for pad in pads):
                        continue
                    if any(o is not t and o.GetLayer() == t.GetLayer() and o.GetNetCode() == t.GetNetCode() and o.HitTest(p, 1) for o in tracks):
                        continue
                    b.Remove(t); GRAVE.append(t); removed += 1
                    break
            if removed == n0:
                break
    return removed


def clip_silk_to_circle(b, cx, cy, r):
    """Drop footprint silkscreen graphics that reach past the round board edge."""
    n = 0
    for fp in b.Footprints():
        for g in list(fp.GraphicalItems()):
            if g.GetLayer() not in (pcbnew.F_SilkS, pcbnew.B_SilkS):
                continue
            bb = g.GetBoundingBox()
            pts = [(bb.GetLeft(), bb.GetTop()), (bb.GetRight(), bb.GetTop()), (bb.GetLeft(), bb.GetBottom()), (bb.GetRight(), bb.GetBottom())]
            if any(math.hypot(pcbnew.ToMM(x) - cx, pcbnew.ToMM(y) - cy) > r for x, y in pts):
                fp.Remove(g); GRAVE.append(g); n += 1
    return n


def tidy_silk(b, hide_prefixes=('R', 'C'), ref_size=0.8):
    for fp in b.Footprints():
        ref = fp.Reference()
        r = fp.GetReference()
        pre = ''.join(ch for ch in r if ch.isalpha())
        if pre in hide_prefixes or pre == 'H':
            ref.SetVisible(False)
        else:
            ref.SetTextSize(pcbnew.VECTOR2I(MM(ref_size), MM(ref_size)))
            ref.SetTextThickness(MM(0.12))
        fp.Value().SetVisible(False)


def _keepouts(b):
    zs = [z for z in b.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    for fp in b.Footprints():
        zs += [z for z in fp.Zones() if z.GetIsRuleArea() and z.GetDoNotAllowVias()]
    return zs


def _dist_seg(px, py, ax, ay, bx, by):
    dx, dy = bx - ax, by - ay
    L = dx * dx + dy * dy
    t = 0 if L == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L))
    qx, qy = ax + t * dx, ay + t * dy
    return math.hypot(px - qx, py - qy)


def stitch(b, net, pts, d=0.6, drill=0.3, clear=0.25, layers_check=None):
    """Add vias of `net` at pts where they don't collide with other-net copper, holes or rule areas."""
    netcode = b.FindNet(net).GetNetCode()
    pads = list(b.GetPads())
    tracks = list(b.GetTracks())
    edge_r = None
    added = 0
    keepouts = _keepouts(b)
    for (x, y) in pts:
        P0 = P(x, y)
        r = d / 2
        bad = False
        for z in keepouts:
            if z.Outline().Contains(P0):
                bad = True; break
        if bad:
            continue
        for pad in pads:
            bb = pad.GetBoundingBox()
            m = MM(r + clear + (0.0 if pad.GetNetCode() == netcode else 0.0))
            if bb.GetLeft() - m < P0.x < bb.GetRight() + m and bb.GetTop() - m < P0.y < bb.GetBottom() + m:
                if pad.GetNetCode() != netcode or pad.HasHole():
                    bad = True; break
        if bad:
            continue
        for t in tracks:
            if t.GetClass() == 'PCB_VIA':
                if math.hypot(pcbnew.ToMM(t.GetPosition().x) - x, pcbnew.ToMM(t.GetPosition().y) - y) < r + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + clear + 0.05:
                    bad = True; break
            else:
                dd = _dist_seg(x, y, pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
                if t.GetNetCode() != netcode and dd < r + pcbnew.ToMM(t.GetWidth()) / 2 + clear:
                    bad = True; break
        if bad:
            continue
        for fp in b.Footprints():
            for pad in fp.Pads():
                pass
        v = add_via(b, net, x, y, d, drill)
        tracks.append(v)
        added += 1
    return added


def _free(b, x, y, r, netcode, clear, cache):
    pads, tracks, keepouts, R0 = cache
    P0 = P(x, y)
    if math.hypot(x - R0[0], y - R0[1]) > R0[2] - r - 0.5:
        return False
    for z in keepouts:
        if z.Outline().Contains(P0):
            return False
    for pad in pads:
        bb = pad.GetBoundingBox()
        m = MM(r + clear)
        if bb.GetLeft() - m < P0.x < bb.GetRight() + m and bb.GetTop() - m < P0.y < bb.GetBottom() + m:
            if pad.GetNetCode() != netcode or pad.HasHole():
                # finer test for same-size round/rect: distance to pad shape
                if pad.GetNetCode() == netcode and not pad.HasHole():
                    continue
                return False
    for t in tracks:
        if t.GetClass() == 'PCB_VIA':
            if math.hypot(pcbnew.ToMM(t.GetPosition().x) - x, pcbnew.ToMM(t.GetPosition().y) - y) < r + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + clear + 0.05:
                return False
        else:
            if t.GetNetCode() == netcode:
                continue
            dd = _dist_seg(x, y, pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y))
            if dd < r + pcbnew.ToMM(t.GetWidth()) / 2 + clear:
                return False
    return True


def _seg_clear(b, x1, y1, x2, y2, w, netcode, clear, pads, skip_pad):
    """True if a track segment does not come near other-net pads (bbox test)."""
    n = max(2, int(math.hypot(x2 - x1, y2 - y1) / 0.1))
    for i in range(n + 1):
        x = x1 + (x2 - x1) * i / n; y = y1 + (y2 - y1) * i / n
        for pad in pads:
            if pad is skip_pad or pad.GetNetCode() == netcode:
                continue
            bb = pad.GetBoundingBox()
            m = MM(w / 2 + clear)
            if bb.GetLeft() - m < MM(x) < bb.GetRight() + m and bb.GetTop() - m < MM(y) < bb.GetBottom() + m:
                return False
    return True


def fanout(b, nets, centre, radius, via_d=0.6, via_drill=0.3, clear=0.2, track_w=0.35, skip_refs=(), dists=(0.0,)):
    """For every SMD pad (top or bottom) on `nets`, drop a via next to it with a short stub."""
    pads = list(b.GetPads())
    keepouts = _keepouts(b)
    tracks = list(b.GetTracks())
    cache = (pads, tracks, keepouts, (centre[0], centre[1], radius))
    done, failed = 0, []
    for pad in pads:
        if pad.GetNetname() not in nets or pad.HasHole():
            continue
        fp = pad.GetParentFootprint()
        if fp.GetReference() in skip_refs:
            continue
        nc = pad.GetNetCode()
        cx, cy = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        bb = pad.GetBoundingBox()
        hw, hh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
        layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
        ok = False
        cands = []
        for extra in (0.35, 0.6, 0.9, 1.3):
            for ang in range(0, 360, 30):
                a = math.radians(ang)
                dx, dy = math.cos(a), math.sin(a)
                # distance from pad centre to its bbox edge along (dx,dy)
                tx = hw / abs(dx) if abs(dx) > 1e-6 else 1e9
                ty = hh / abs(dy) if abs(dy) > 1e-6 else 1e9
                d = min(tx, ty) + via_d / 2 + extra
                cands.append((cx + dx * d, cy + dy * d))
        for (x, y) in cands:
            if not _free(b, x, y, via_d / 2, nc, clear, cache):
                continue
            # stub from pad centre to via must not pass other-net pads
            if not _seg_clear(b, cx, cy, x, y, track_w, nc, clear, pads, pad):
                continue
            v = add_via(b, pad.GetNetname(), x, y, via_d, via_drill)
            add_track(b, pad.GetNetname(), layer, [(cx, cy), (x, y)], track_w)
            tracks.append(v)
            for t in b.GetTracks():
                pass
            tracks[:] = list(b.GetTracks())
            ok = True
            done += 1
            break
        if not ok:
            failed.append('%s.%s' % (fp.GetReference(), pad.GetNumber()))
    return done, failed


def fanout_one(b, pad, centre, radius, via_d=0.6, via_drill=0.3, clear=0.2, track_w=0.2):
    """Drop one via next to `pad` with a stub on the pad's layer. Returns (1, []) or (0, [name])."""
    pads = list(b.GetPads())
    keepouts = _keepouts(b)
    tracks = list(b.GetTracks())
    cache = (pads, tracks, keepouts, (centre[0], centre[1], radius))
    nc = pad.GetNetCode()
    cx, cy = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
    bb = pad.GetBoundingBox()
    hw, hh = pcbnew.ToMM(bb.GetWidth()) / 2, pcbnew.ToMM(bb.GetHeight()) / 2
    layer = pcbnew.F_Cu if pad.IsOnLayer(pcbnew.F_Cu) else pcbnew.B_Cu
    for extra in (0.3, 0.6, 0.9, 1.3, 1.8, 2.4, 3.0, 3.6):
        for ang in range(0, 360, 10):
            a = math.radians(ang)
            dx, dy = math.cos(a), math.sin(a)
            tx = hw / abs(dx) if abs(dx) > 1e-6 else 1e9
            ty = hh / abs(dy) if abs(dy) > 1e-6 else 1e9
            d = min(tx, ty) + via_d / 2 + extra
            x, y = cx + dx * d, cy + dy * d
            if not _free(b, x, y, via_d / 2, nc, clear, cache):
                continue
            if not _seg_clear(b, cx, cy, x, y, track_w, nc, clear, pads, pad):
                continue
            # stub must also stay clear of other-net tracks on its layer
            bad = False
            for t in tracks:
                if t.GetNetCode() == nc:
                    continue
                if t.GetClass() == 'PCB_VIA':
                    vx, vy = pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y)
                    if _dist_seg(vx, vy, cx, cy, x, y) < track_w / 2 + pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + clear:
                        bad = True; break
                    continue
                if t.GetLayer() != layer:
                    continue
                for k in range(11):
                    px, py = cx + (x - cx) * k / 10, cy + (y - cy) * k / 10
                    if _dist_seg(px, py, pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y)) < track_w / 2 + pcbnew.ToMM(t.GetWidth()) / 2 + clear:
                        bad = True; break
                if bad:
                    break
            if bad:
                continue
            v = add_via(b, pad.GetNetname(), x, y, via_d, via_drill)
            add_track(b, pad.GetNetname(), layer, [(cx, cy), (x, y)], track_w)
            return v, []
    return 0, [pad.GetParentFootprint().GetReference() + '.' + pad.GetNumber()]
