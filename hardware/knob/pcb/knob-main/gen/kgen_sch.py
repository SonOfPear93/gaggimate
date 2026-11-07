"""Tiny KiCad schematic generator: symbols placed on a grid, every connected pin gets a
local net label at its connection point, every unused pin gets a no-connect flag.
Writes KiCad 8 format (20231120); run `kicad-cli sch upgrade` afterwards."""
import uuid, copy, os, json, math
from sexp import parse, dump, Str, find, find1

SYMDIR = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols'
_libcache = {}
EXTRA_LIBS = {}  # libname -> path


def U(*a):
    return str(uuid.uuid5(uuid.NAMESPACE_URL, '/'.join(map(str, a))))


def _lib(libname):
    if libname not in _libcache:
        path = EXTRA_LIBS.get(libname, os.path.join(SYMDIR, libname + '.kicad_sym'))
        d = parse(open(path).read())[0]
        _libcache[libname] = {s[1]: s for s in find(d, 'symbol')}
    return _libcache[libname]


def flat(libname, name):
    syms = _lib(libname)
    s = syms[name]
    ex = find1(s, 'extends')
    if not ex:
        return copy.deepcopy(s)
    parent = flat(libname, ex[1])
    pname = parent[1]
    out = ['symbol', Str(name)]
    child_attr = {e[0]: e for e in s[2:] if isinstance(e, list) and e[0] not in ('property', 'symbol', 'extends')}
    for e in parent[2:]:
        if isinstance(e, list) and e[0] in ('property', 'symbol'):
            continue
        if isinstance(e, list) and e[0] in child_attr:
            out.append(copy.deepcopy(child_attr.pop(e[0])))
        else:
            out.append(copy.deepcopy(e))
    for e in child_attr.values():
        out.append(copy.deepcopy(e))
    cprops = {p[1]: p for p in find(s, 'property')}
    for p in find(parent, 'property'):
        out.append(copy.deepcopy(cprops.pop(p[1], p)))
    for p in cprops.values():
        out.append(copy.deepcopy(p))
    for u in find(parent, 'symbol'):
        u2 = copy.deepcopy(u)
        u2[1] = Str(name + u[1][len(pname):])
        out.append(u2)
    return out


def pins_of(sym, unit=1):
    res = []
    for u in find(sym, 'symbol'):
        parts = u[1].rsplit('_', 2)
        un, st = int(parts[1]), int(parts[2])
        if un not in (0, unit) or st not in (0, 1):
            continue
        for p in find(u, 'pin'):
            at = find1(p, 'at')
            res.append(dict(type=p[1], name=find1(p, 'name')[1], num=find1(p, 'number')[1],
                            x=float(at[1]), y=float(at[2]), ang=int(float(at[3])) if len(at) > 3 else 0,
                            length=float(find1(p, 'length')[1])))
    return res


def body_extent(sym):
    xs, ys = [0.0], [0.0]
    for u in find(sym, 'symbol'):
        for e in u[2:]:
            if not isinstance(e, list):
                continue
            if e[0] == 'pin':
                at = find1(e, 'at'); xs.append(float(at[1])); ys.append(float(at[2]))
            for k in ('start', 'end', 'center'):
                q = find1(e, k)
                if q:
                    xs.append(float(q[1])); ys.append(float(q[2]))
            pts = find1(e, 'pts')
            if pts:
                for xy in find(pts, 'xy'):
                    xs.append(float(xy[1])); ys.append(float(xy[2]))
    return min(xs), max(xs), min(ys), max(ys)


def snap(v, g=1.27):
    return round(round(v / g) * g, 4)


def prop(name, val, x, y, hide=False, ang=0, justify=None):
    eff = ['effects', ['font', ['size', 1.27, 1.27]]]
    if justify:
        eff.append(['justify', justify])
    if hide:
        eff.append(['hide', 'yes'])
    return ['property', Str(name), Str(val), ['at', x, y, ang], eff]


class Comp:
    def __init__(self, ref, lib_id, value, footprint='', lcsc='', pins=None, in_bom=True, on_board=True,
                 desc='', fields=None, dnp=False, mpn=''):
        self.ref, self.lib_id, self.value, self.footprint, self.lcsc = ref, lib_id, value, footprint, lcsc
        self.pinmap = dict(pins or {})
        self.in_bom, self.on_board, self.desc, self.dnp = in_bom, on_board, desc, dnp
        self.fields = dict(fields or {})
        if mpn:
            self.fields['MPN'] = mpn
        lib, name = lib_id.split(':')
        self.sym = flat(lib, name)
        self.pins = pins_of(self.sym)
        nums = {p['num'] for p in self.pins}
        for k in self.pinmap:
            if k not in nums:
                raise ValueError('%s: pin %s not in symbol %s (%s)' % (ref, k, lib_id, sorted(nums)))
        self.uuid = U('sym', ref)


class Sheet:
    def __init__(self, project, title, paper='A1', rev='1', comments=()):
        self.project, self.title, self.paper, self.rev, self.comments = project, title, paper, rev, comments
        self.comps = []
        self.texts = []
        self.flags = []  # nets that need PWR_FLAG
        self.root = U('root', project)
        self.groups = []

    def add(self, c, group=None):
        self.comps.append((c, group))
        return c

    def text(self, s, x, y, size=1.5):
        self.texts.append((s, x, y, size))

    def write(self, path, origin=(25.4, 30.48), maxw=760):
        items = []
        lib_syms = {}
        labels, ncs = [], []
        # layout: grouped flow layout
        x0, y0 = origin
        cx, cy, rowh = x0, y0, 0
        cur_group = None
        allc = [(c, g) for c, g in self.comps]
        for f in self.flags:
            fc = Comp('#FLG%02d' % (len([1 for _ in self.flags[:self.flags.index(f)]]) + 1), 'power:PWR_FLAG', 'PWR_FLAG',
                      pins={'1': f}, in_bom=False, on_board=False)
            allc.append((fc, 'flags'))
        for c, g in allc:
            xmin, xmax, ymin, ymax = body_extent(c.sym)
            # label allowance
            lab = max([len(n) for n in c.pinmap.values()] + [4]) * 1.0 + 4
            lx = lab if any(p['ang'] == 0 and p['num'] in c.pinmap for p in c.pins) else 3
            rx = lab if any(p['ang'] == 180 and p['num'] in c.pinmap for p in c.pins) else 3
            ty = lab if any(p['ang'] == 270 and p['num'] in c.pinmap for p in c.pins) else 3
            by = lab if any(p['ang'] == 90 and p['num'] in c.pinmap for p in c.pins) else 3
            w = (xmax - xmin) + lx + rx + 6
            h = (ymax - ymin) + ty + by + 8
            if g != cur_group and cur_group is not None:
                # new group starts new row
                cx = x0; cy += rowh + 10; rowh = 0
            cur_group = g
            if cx + w > x0 + maxw:
                cx = x0; cy += rowh + 4; rowh = 0
            X = snap(cx + lx - xmin, 2.54)
            Y = snap(cy + ty + ymax + 3, 2.54)
            cx += w; rowh = max(rowh, h)
            self._place(c, X, Y, ymin, ymax, items, lib_syms, labels, ncs)
        out = ['kicad_sch', ['version', 20231120], ['generator', Str('eeschema')], ['generator_version', Str('8.0')],
               ['uuid', Str(self.root)], ['paper', Str(self.paper)],
               ['title_block', ['title', Str(self.title)], ['date', Str('2026-11-07')], ['rev', Str(self.rev)],
                ['company', Str('GaggiMate Knob')]] + [['comment', i + 1, Str(s)] for i, s in enumerate(self.comments)],
               ['lib_symbols'] + list(lib_syms.values())]
        for (s, x, y, size) in self.texts:
            out.append(['text', Str(s), ['exclude_from_sim', 'no'], ['at', x, y, 0],
                        ['effects', ['font', ['size', size, size]], ['justify', 'left', 'top']], ['uuid', Str(U('text', s[:40], x, y))]])
        for (x, y) in ncs:
            out.append(['no_connect', ['at', x, y], ['uuid', Str(U('nc', x, y))]])
        for (net, x, y, ang) in labels:
            just = ['justify', 'left', 'bottom'] if ang in (0, 90) else ['justify', 'right', 'bottom']
            out.append(['label', Str(net), ['at', x, y, ang], ['fields_autoplaced', 'yes'],
                        ['effects', ['font', ['size', 1.27, 1.27]], just], ['uuid', Str(U('lbl', net, x, y))]])
        out += items
        out.append(['sheet_instances', ['path', Str('/'), ['page', Str('1')]]])
        open(path, 'w').write(dump(out) + '\n')

    def _place(self, c, X, Y, ymin, ymax, items, lib_syms, labels, ncs):
        lib, name = c.lib_id.split(':')
        if c.lib_id not in lib_syms:
            ls = copy.deepcopy(c.sym)
            ls[1] = Str(c.lib_id)
            lib_syms[c.lib_id] = ls
        props = {p[1]: p[2] for p in find(c.sym, 'property')}
        s = ['symbol', ['lib_id', Str(c.lib_id)], ['at', X, Y, 0], ['unit', 1],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes' if c.in_bom else 'no'], ['on_board', 'yes' if c.on_board else 'no'],
             ['dnp', 'yes' if c.dnp else 'no'], ['uuid', Str(c.uuid)]]
        hide_ref = c.ref.startswith('#')
        s.append(prop('Reference', c.ref, X, snap(Y - ymax - 2.54), hide=hide_ref))
        s.append(prop('Value', c.value, X, snap(Y - ymin + 2.54), hide=hide_ref))
        s.append(prop('Footprint', c.footprint, X, Y, hide=True))
        s.append(prop('Datasheet', props.get('Datasheet', '~'), X, Y, hide=True))
        s.append(prop('Description', c.desc or props.get('Description', ''), X, Y, hide=True))
        if c.lcsc:
            s.append(prop('LCSC', c.lcsc, X, Y, hide=True))
        for k, v in c.fields.items():
            s.append(prop(k, v, X, Y, hide=True))
        seen = set()
        for p in c.pins:
            s.append(['pin', Str(p['num']), ['uuid', Str(U('pin', c.ref, p['num']))]])
        s.append(['instances', ['project', Str(self.project), ['path', Str('/' + self.root), ['reference', Str(c.ref)], ['unit', 1]]]])
        items.append(s)
        # labels / no-connects
        bypos = {}
        for p in c.pins:
            pos = (round(X + p['x'], 4), round(Y - p['y'], 4))
            bypos.setdefault(pos, []).append(p)
        for pos, ps in bypos.items():
            nets = {c.pinmap[p['num']] for p in ps if p['num'] in c.pinmap}
            if len(nets) > 1:
                raise ValueError('%s: stacked pins %s with different nets %s' % (c.ref, [p['num'] for p in ps], nets))
            if nets:
                ang = {0: 180, 180: 0, 90: 270, 270: 90}[ps[0]['ang']]
                labels.append((nets.pop(), pos[0], pos[1], ang))
            else:
                ncs.append(pos)

    def unconnected_report(self):
        out = []
        for c, g in self.comps:
            for p in c.pins:
                if p['num'] not in c.pinmap and p['type'] not in ('no_connect',):
                    out.append('%s.%s(%s)' % (c.ref, p['num'], p['name']))
        return out


def write_pro(path, name, classes, patterns, rules=None, extra=None):
    d = {
        "board": {"design_settings": {"defaults": {}, "diff_pair_dimensions": [], "drc_exclusions": [],
                                      "rules": rules or {}, "track_widths": [], "via_dimensions": []}},
        "boards": [], "libraries": {"pinned_footprint_libs": [], "pinned_symbol_libs": []},
        "meta": {"filename": name + ".kicad_pro", "version": 1},
        "net_settings": {"classes": classes, "meta": {"version": 3}, "net_colors": None,
                         "netclass_assignments": None, "netclass_patterns": patterns},
        "pcbnew": {"page_layout_descr_file": ""}, "sheets": [], "text_variables": {}}
    if extra:
        for k, v in extra.items():
            d[k] = v
    json.dump(d, open(path, 'w'), indent=2)


def netclass(name, track, clearance=0.2, via_d=0.6, via_drill=0.3):
    return {"bus_width": 12, "clearance": clearance, "diff_pair_gap": 0.2, "diff_pair_via_gap": 0.25,
            "diff_pair_width": 0.2, "line_style": 0, "microvia_diameter": 0.3, "microvia_drill": 0.1,
            "name": name, "pcb_color": "rgba(0, 0, 0, 0.000)", "schematic_color": "rgba(0, 0, 0, 0.000)",
            "track_width": track, "via_diameter": via_d, "via_drill": via_drill, "wire_width": 6}
