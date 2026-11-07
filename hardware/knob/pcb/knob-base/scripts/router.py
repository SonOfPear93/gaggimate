"""Tiny 2-layer grid maze router (A*, 8-direction, vias) used by gen_pcb.py.

Not a general autorouter: it routes the few signal nets of this board on a
0.1 mm grid with clearance-inflated obstacles, then straightens the paths.
KiCad DRC remains the authority on the result.
"""
import heapq
import math
from array import array

import pcbnew as pcb

G = 0.1            # grid pitch, mm
HALF = 37.6        # grid covers [-HALF, HALF] around board centre
N = int(round(2 * HALF / G)) + 1
NN = N * N
CLR = 0.15         # copper clearance
MARGIN = 0.08      # grid quantisation margin
EDGE_CLR = 0.3
VIA_D, VIA_DRILL = 0.6, 0.3
VIA_COST = 25.0
SQ2 = math.sqrt(2)


def cell(u, v):
    i = int(round((u + HALF) / G))
    j = int(round((v + HALF) / G))
    if 0 <= i < N and 0 <= j < N:
        return j * N + i
    return None


def uv(c):
    return (-HALF + (c % N) * G, -HALF + (c // N) * G)


class Router:
    def __init__(self, board, width=0.25, keepout=None, maxw=0.25):
        self.b = board
        self.w = width
        self.hw = width / 2
        self.maxhw = maxw / 2
        self.occ = [array('i', [-1]) * NN, array('i', [-1]) * NN]
        self.ok = bytearray(NN)   # board area usable by a track centreline
        poly = pcb.SHAPE_POLY_SET()
        board.GetBoardPolygonOutlines(poly, False)
        dpoly = pcb.SHAPE_POLY_SET(poly)
        dpoly.Deflate(pcb.FromMM(EDGE_CLR + self.hw + MARGIN), pcb.CORNER_STRATEGY_ROUND_ALL_CORNERS, pcb.FromMM(0.005))
        for c in range(NN):
            u, v = uv(c)
            if u * u + v * v > 37.5 ** 2:
                continue
            if keepout and keepout(u, v):
                continue
            if dpoly.Contains(pcb.VECTOR2I(pcb.FromMM(100 + u), pcb.FromMM(100 + v))):
                self.ok[c] = 1
        self.netcode = {}
        self.novia = bytearray(NN)

    # ------------------------------------------------------------ marking ----
    def _mark(self, layer, c, net):
        o = self.occ[layer][c]
        if o == -1:
            self.occ[layer][c] = net
        elif o != net:
            self.occ[layer][c] = -2

    def mark_poly(self, poly, layers, net):
        bb = poly.BBox()
        u0, v0 = pcb.ToMM(bb.GetLeft()) - 100, pcb.ToMM(bb.GetTop()) - 100
        u1, v1 = pcb.ToMM(bb.GetRight()) - 100, pcb.ToMM(bb.GetBottom()) - 100
        i0, i1 = int((u0 + HALF) / G) - 1, int((u1 + HALF) / G) + 2
        j0, j1 = int((v0 + HALF) / G) - 1, int((v1 + HALF) / G) + 2
        for j in range(max(j0, 0), min(j1, N)):
            for i in range(max(i0, 0), min(i1, N)):
                u, v = -HALF + i * G, -HALF + j * G
                if poly.Contains(pcb.VECTOR2I(pcb.FromMM(100 + u), pcb.FromMM(100 + v))):
                    for L in layers:
                        self._mark(L, j * N + i, net)

    def add_pad(self, pad):
        net = pad.GetNetCode() if pad.GetNetCode() > 0 else -3
        layers = []
        if pad.IsOnLayer(pcb.F_Cu):
            layers.append(0)
        if pad.IsOnLayer(pcb.B_Cu):
            layers.append(1)
        lid = pcb.F_Cu if 0 in layers else pcb.B_Cu
        poly = pcb.SHAPE_POLY_SET()
        pad.TransformShapeToPolygon(poly, lid, pcb.FromMM(CLR + self.hw + MARGIN), pcb.FromMM(0.005), pcb.ERROR_OUTSIDE)
        if net == -3:
            for L in layers:
                self.mark_poly_block(poly, L)
        else:
            self.mark_poly(poly, layers, net)
        if pad.HasHole():
            pass

    def mark_novia(self, poly):
        bb = poly.BBox()
        u0, v0 = pcb.ToMM(bb.GetLeft()) - 100, pcb.ToMM(bb.GetTop()) - 100
        u1, v1 = pcb.ToMM(bb.GetRight()) - 100, pcb.ToMM(bb.GetBottom()) - 100
        for j in range(max(int((v0 + HALF) / G) - 1, 0), min(int((v1 + HALF) / G) + 2, N)):
            for i in range(max(int((u0 + HALF) / G) - 1, 0), min(int((u1 + HALF) / G) + 2, N)):
                u, v = -HALF + i * G, -HALF + j * G
                if poly.Contains(pcb.VECTOR2I(pcb.FromMM(100 + u), pcb.FromMM(100 + v))):
                    self.novia[j * N + i] = 1

    def mark_poly_block(self, poly, layer):
        bb = poly.BBox()
        u0, v0 = pcb.ToMM(bb.GetLeft()) - 100, pcb.ToMM(bb.GetTop()) - 100
        u1, v1 = pcb.ToMM(bb.GetRight()) - 100, pcb.ToMM(bb.GetBottom()) - 100
        for j in range(max(int((v0 + HALF) / G) - 1, 0), min(int((v1 + HALF) / G) + 2, N)):
            for i in range(max(int((u0 + HALF) / G) - 1, 0), min(int((u1 + HALF) / G) + 2, N)):
                u, v = -HALF + i * G, -HALF + j * G
                if poly.Contains(pcb.VECTOR2I(pcb.FromMM(100 + u), pcb.FromMM(100 + v))):
                    self.occ[layer][j * N + i] = -2

    def mark_seg(self, layers, a, b, net, radius):
        (ua, va), (ub, vb) = a, b
        du, dv = ub - ua, vb - va
        L2 = du * du + dv * dv
        for j in range(max(int((min(va, vb) - radius + HALF) / G) - 1, 0), min(int((max(va, vb) + radius + HALF) / G) + 2, N)):
            for i in range(max(int((min(ua, ub) - radius + HALF) / G) - 1, 0), min(int((max(ua, ub) + radius + HALF) / G) + 2, N)):
                u, v = -HALF + i * G, -HALF + j * G
                t = 0.0 if L2 == 0 else max(0.0, min(1.0, ((u - ua) * du + (v - va) * dv) / L2))
                pu, pv = ua + t * du - u, va + t * dv - v
                if pu * pu + pv * pv <= radius * radius:
                    for L in layers:
                        self._mark(L, j * N + i, net)

    def add_track(self, layer, a, b, net, width):
        self.mark_seg([layer], a, b, net, width / 2 + CLR + self.hw + MARGIN)

    def add_via(self, p, net):
        self.mark_seg([0, 1], p, p, net, VIA_D / 2 + CLR + self.hw + MARGIN)

    # ------------------------------------------------------------- search ----
    def free(self, L, c, net):
        o = self.occ[L][c]
        return self.ok[c] and (o == -1 or o == net)

    def via_ok(self, c, net):
        if self.novia[c]:
            return False
        i, j = c % N, c // N
        for dj in (-2, -1, 0, 1, 2):
            for di in (-2, -1, 0, 1, 2):
                if di * di + dj * dj > 5:
                    continue
                cc = (j + dj) * N + (i + di)
                if not (self.free(0, cc, net) and self.free(1, cc, net)):
                    return False
        return True

    def astar(self, net, sources, targets, prefer=None):
        """sources/targets: sets of (layer, cell). Returns list of (layer, cell)."""
        tgt = targets
        tc = [uv(c) for (_, c) in targets]
        tu0, tu1 = min(p[0] for p in tc), max(p[0] for p in tc)
        tv0, tv1 = min(p[1] for p in tc), max(p[1] for p in tc)

        def h(c):
            u, v = uv(c)
            du = max(tu0 - u, 0, u - tu1) / G
            dv = max(tv0 - v, 0, v - tv1) / G
            return max(du, dv) + (SQ2 - 1) * min(du, dv)

        gs = {}
        came = {}
        pq = []
        for s in sources:
            gs[s] = 0.0
            heapq.heappush(pq, (h(s[1]), 0.0, s))
        nb = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
              (1, 1, SQ2), (1, -1, SQ2), (-1, 1, SQ2), (-1, -1, SQ2)]
        expanded = 0
        while pq:
            f, g, s = heapq.heappop(pq)
            if gs.get(s, 1e18) < g:
                continue
            if s in tgt:
                path = [s]
                while path[-1] in came:
                    path.append(came[path[-1]])
                return path[::-1]
            expanded += 1
            if expanded > 1500000:
                return None
            L, c = s
            i, j = c % N, c // N
            lc = 1.0 if prefer is None or prefer == L else 1.6
            for di, dj, w in nb:
                ii, jj = i + di, j + dj
                if not (0 <= ii < N and 0 <= jj < N):
                    continue
                cc = jj * N + ii
                if not self.free(L, cc, net):
                    continue
                if di and dj and not (self.free(L, j * N + ii, net) or self.free(L, jj * N + i, net)):
                    continue
                ns = (L, cc)
                ng = g + w * lc
                if ng < gs.get(ns, 1e18):
                    gs[ns] = ng
                    came[ns] = s
                    heapq.heappush(pq, (ng + h(cc), ng, ns))
            ns = (1 - L, c)
            if ns not in gs or gs[ns] > g + VIA_COST:
                if self.via_ok(c, net):
                    ng = g + VIA_COST
                    if ng < gs.get(ns, 1e18):
                        gs[ns] = ng
                        came[ns] = s
                        heapq.heappush(pq, (ng + h(c), ng, ns))
        return None

    def seg_free(self, L, a, b, net):
        (ua, va), (ub, vb) = a, b
        d = math.hypot(ub - ua, vb - va)
        n = max(1, int(d / 0.04))
        for k in range(n + 1):
            t = k / n
            c = cell(ua + t * (ub - ua), va + t * (vb - va))
            if c is None or not self.free(L, c, net):
                return False
        return True

    def simplify(self, path, net):
        """Split into same-layer runs, straighten each run (any angle)."""
        runs = []
        cur = [path[0]]
        for s in path[1:]:
            if s[0] != cur[-1][0]:
                runs.append(cur)
                cur = [s]
            else:
                cur.append(s)
        runs.append(cur)
        out = []
        for run in runs:
            L = run[0][0]
            pts = [uv(c) for _, c in run]
            keep = [pts[0]]
            i = 0
            while i < len(pts) - 1:
                j = len(pts) - 1
                while j > i + 1 and not self.seg_free(L, pts[i], pts[j], net):
                    j -= 1
                keep.append(pts[j])
                i = j
            out.append((L, keep))
        return out
