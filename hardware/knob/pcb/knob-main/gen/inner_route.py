"""Finish the last few connections Freerouting leaves open by routing them on In2 (the +3V3 plane layer):
via next to each SMD end (short F.Cu stub), then a grid A* route on In2. The +3V3 pour later flows around them.
inner_route.py board.kicad_pcb NET:REF.PAD:REF.PAD [...]"""
import os, sys, math, heapq
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pcbnew
from kgen_pcb import *

pcb = sys.argv[1]
jobs = [a.split(':') for a in sys.argv[2:]]
b = pcbnew.LoadBoard(pcb)
CX, CY, RB = 100.0, 100.0, 37.0
G = 0.1                       # grid mm
W = 0.2                       # track width on In2
CLR = 0.22                    # clearance used for obstacles (rule 0.15/0.2 + margin)
N = int(2 * RB / G) + 1
LAYER = pcbnew.In2_Cu


def cell(x, y):
    return int(round((x - (CX - RB)) / G)), int(round((y - (CY - RB)) / G))


def xy(i, j):
    return CX - RB + i * G, CY - RB + j * G


def find_pad(ref, num):
    fp = b.FindFootprintByReference(ref)
    for p in fp.Pads():
        if p.GetNumber() == num:
            return p
    raise KeyError(ref + '.' + num)


def build_grid(netcode):
    blocked = bytearray(N * N)
    def circ(x, y, r):
        i0, j0 = cell(x - r, y - r); i1, j1 = cell(x + r, y + r)
        for i in range(max(0, i0), min(N, i1 + 1)):
            for j in range(max(0, j0), min(N, j1 + 1)):
                px, py = xy(i, j)
                if (px - x) ** 2 + (py - y) ** 2 <= r * r:
                    blocked[i * N + j] = 1
    def seg(x1, y1, x2, y2, r):
        L = math.hypot(x2 - x1, y2 - y1)
        n = max(1, int(L / (G / 2)))
        for k in range(n + 1):
            circ(x1 + (x2 - x1) * k / n, y1 + (y2 - y1) * k / n, r)
    for i in range(N):
        for j in range(N):
            px, py = xy(i, j)
            if math.hypot(px - CX, py - CY) > RB - 0.5 - W / 2:
                blocked[i * N + j] = 1
    for z in b.Zones():
        if z.GetIsRuleArea() and z.GetDoNotAllowTracks() and z.IsOnLayer(LAYER):
            bb = z.GetBoundingBox()
            i0, j0 = cell(pcbnew.ToMM(bb.GetLeft()), pcbnew.ToMM(bb.GetTop()))
            i1, j1 = cell(pcbnew.ToMM(bb.GetRight()), pcbnew.ToMM(bb.GetBottom()))
            for i in range(max(0, i0 - 3), min(N, i1 + 4)):
                for j in range(max(0, j0 - 3), min(N, j1 + 4)):
                    px, py = xy(i, j)
                    blocked[i * N + j] = 1
    for t in b.GetTracks():
        if t.GetNetCode() == netcode:
            continue
        if t.GetClass() == 'PCB_VIA':
            circ(pcbnew.ToMM(t.GetPosition().x), pcbnew.ToMM(t.GetPosition().y), pcbnew.ToMM(t.GetWidth(pcbnew.F_Cu)) / 2 + CLR + W / 2)
        elif t.GetLayer() == LAYER:
            seg(pcbnew.ToMM(t.GetStart().x), pcbnew.ToMM(t.GetStart().y), pcbnew.ToMM(t.GetEnd().x), pcbnew.ToMM(t.GetEnd().y),
                pcbnew.ToMM(t.GetWidth()) / 2 + CLR + W / 2)
    for p in b.GetPads():
        if p.GetNetCode() == netcode and p.GetNetCode() != 0:
            continue
        if p.HasHole():
            bb = p.GetBoundingBox()
            r = max(pcbnew.ToMM(bb.GetWidth()), pcbnew.ToMM(bb.GetHeight())) / 2
            circ(pcbnew.ToMM(p.GetPosition().x), pcbnew.ToMM(p.GetPosition().y), r + CLR + W / 2)
    return blocked


def astar(blocked, a, c):
    sx, sy = a; tx, ty = c
    for (i, j) in (a, c):
        for di in range(-3, 4):
            for dj in range(-3, 4):
                if 0 <= i + di < N and 0 <= j + dj < N:
                    blocked[(i + di) * N + j + dj] = 0
    D = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0), (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]
    h = lambda i, j: max(abs(i - tx), abs(j - ty)) + 0.414 * min(abs(i - tx), abs(j - ty))
    openq = [(h(sx, sy), 0.0, sx, sy, -1)]
    came, gbest = {}, {(sx, sy): 0.0}
    while openq:
        f, g, i, j, d = heapq.heappop(openq)
        if (i, j) == (tx, ty):
            path = [(i, j)]
            while (i, j) in came:
                i, j = came[(i, j)]
                path.append((i, j))
            return path[::-1]
        if g > gbest.get((i, j), 1e18):
            continue
        for k, (di, dj, cst) in enumerate(D):
            ni, nj = i + di, j + dj
            if not (0 <= ni < N and 0 <= nj < N) or blocked[ni * N + nj]:
                continue
            ng = g + cst + (0.3 if d not in (-1, k) else 0)
            if ng < gbest.get((ni, nj), 1e18):
                gbest[(ni, nj)] = ng; came[(ni, nj)] = (i, j)
                heapq.heappush(openq, (ng + h(ni, nj), ng, ni, nj, k))
    return None


def simplify(path):
    out = [path[0]]
    for k in range(1, len(path) - 1):
        a, m, c = out[-1], path[k], path[k + 1]
        if (m[0] - a[0]) * (c[1] - m[1]) != (m[1] - a[1]) * (c[0] - m[0]):
            out.append(m)
    out.append(path[-1])
    return out


ok = True
for job in jobs:
    net = job[0]
    netcode = b.FindNet(net).GetNetCode()
    ends = []
    added = []
    for e in job[1:]:
        ref, num = e.split('.')
        pad = find_pad(ref, num)
        x, y = pcbnew.ToMM(pad.GetPosition().x), pcbnew.ToMM(pad.GetPosition().y)
        if pad.HasHole():
            ends.append((x, y))
            continue
        # via next to the pad, short F.Cu stub (reuse the fan-out search)
        tracks_before = len(list(b.GetTracks()))
        v, failed = fanout_one(b, pad, (CX, CY), RB, 0.6, 0.3, 0.2, 0.2)
        if not v:
            print('no via spot for', e); ok = False; break
        added.append(v)
        added.append([t for t in b.GetTracks() if t.GetClass() == 'PCB_TRACK' and t.GetNetCode() == netcode][-1])
        ends.append((pcbnew.ToMM(v.GetPosition().x), pcbnew.ToMM(v.GetPosition().y)))
    if len(ends) != 2:
        for it in added:
            b.Remove(it); GRAVE.append(it)
        continue
    blocked = build_grid(netcode)
    path = astar(blocked, cell(*ends[0]), cell(*ends[1]))
    if not path:
        print('no In2 path for', net); ok = False; continue
    pts = [xy(i, j) for (i, j) in simplify(path)]
    pts[0], pts[-1] = ends[0], ends[-1]
    add_track(b, net, LAYER, pts, W)
    print('routed %s on In2: %d segments, %.1f mm' % (net, len(pts) - 1, sum(math.hypot(x2 - x1, y2 - y1) for (x1, y1), (x2, y2) in zip(pts, pts[1:]))))
fill_zones(b)
pcbnew.SaveBoard(pcb, b)
print('saved', ok)
