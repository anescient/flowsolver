#!/usr/bin/env python

import random
from copy import deepcopy
from itertools import combinations
from functools import reduce
from graph import SimpleGraph, QueryableSimpleGraph, OnlineReducedGraph


def _testGraph():
    g = SimpleGraph()
    assert isinstance(g, QueryableSimpleGraph)
    assert not isinstance(g.asReadOnly(), SimpleGraph)
    assert isinstance(g.asReadOnly(), QueryableSimpleGraph)
    g.assertSimple()
    verts = []
    for i in range(10):
        verts.append(g.pushVertex())
    try:
        g.addVertex(verts[0])
        raise AssertionError
    except ValueError:
        pass
    assert len(set(verts)) == len(verts)
    for v in verts:
        assert not g.adjacencies(v)
        assert g.connectedComponent(v) == {v}
        assert not g.isSeparator(v)
        assert g.isConnectedSet([v])
    parts = g.disjointPartitions()
    assert len(parts) == len(verts)
    s = set()
    for p in parts:
        assert len(p) == 1
        s.add(p.pop())
    assert s == set(verts)
    edgeCount = 0
    assert g.edgeCount() == edgeCount
    assert g.edgeCount(without=set()) == g.edgeCount()
    for i in range(len(verts) - 1):
        edgeCount += 1
        g.addEdge(verts[i], verts[i + 1])
        for v in verts[i + 2:]:
            assert not g.connected(verts[i + 1], v)
            assert not g.connected(v, verts[i + 1])
        for j in range(i + 1):
            if j > 0:
                assert g.connected(verts[0], verts[j])
                assert g.connected(verts[j], verts[0])
            assert g.connectedComponent(verts[j]) == set(verts[:i + 2])
        assert g.edgeCount() == edgeCount
    assert g.edgeCount(without=set()) == g.edgeCount()
    assert g.edgeCount(mask=verts) == g.edgeCount()
    for v in verts:
        assert g.edgeCount(mask={v}) == 0
        assert g.connectedComponent(v) == set(verts)
    assert g.isConnectedSet(verts)
    assert g.isConnectedSet([verts[2], verts[4]], verts[2:5])
    assert not g.isConnectedSet([verts[2], verts[4]], [verts[2], verts[4]])
    assert g.isConnectedSet(verts[:4] + verts[5:])
    assert not g.isConnectedSet(verts[:4] + verts[5:], verts[:4] + verts[5:])
    assert not g.isSeparator(verts[0])
    assert not g.isSeparator(verts[-1])
    assert all(g.isSeparator(v) for v in verts[1:-1])
    assert g.shortestPath(verts[0], verts[-1]) == verts
    assert g.shortestPath(verts[-1], verts[0]) == list(reversed(verts))
    assert g.shortestPath(verts[3], verts[3]) == [verts[3]]

    shortcut = g.pushVertex()
    edgeCount += 2
    g.addEdge(verts[0], shortcut)
    g.addEdge(verts[-1], shortcut)
    assert g.shortestPath(verts[0], verts[-1]) == \
        [verts[0], shortcut, verts[-1]]

    assert verts[0] == 0
    edgeCount -= 1
    g.removeEdge(verts[-1], shortcut)
    assert g.shortestPath(shortcut, verts[1]) == [shortcut, verts[0], verts[1]]
    edgeCount -= len(g.adjacencies(shortcut))
    assert g.edgeCount(without={shortcut}) == edgeCount
    g.removeVertex(shortcut)
    assert g.edgeCount() == edgeCount
    # noinspection PyUnusedLocal
    edgeCount = None

    g.addEdge(verts[0], verts[-1])
    assert g.shortestPath(verts[0], verts[-1]) == [verts[0], verts[-1]]
    assert not any(g.isSeparator(v) for v in verts)
    g.removeEdge(verts[0], verts[-1])
    g.asReadOnly()
    mask = verts[:2] + verts[3:]
    parts = g.disjointPartitions(mask)
    assert len(parts) == 2
    assert not parts[0].intersection(parts[1])
    assert g.isConnectedSet(parts[0])
    assert g.isConnectedSet(parts[1])
    for v1 in parts[0]:
        for v2 in parts[1]:
            assert g.shortestPath(v1, v2, mask) == []
    assert not g.isConnectedSet(mask, mask)
    assert verts[2] not in parts[0].union(parts[1])
    assert parts[0].union(parts[1]) == set(verts) - set(verts[2:3])
    drops = [verts[i] for i in [2, 5, 8]]
    for v in drops:
        g.removeVertex(v)
        verts.remove(v)
    assert not g.adjacencies(verts[-1])
    for v in verts[:-1]:
        assert len(g.adjacencies(v)) == 1
        assert not g.isSeparator(v)
    g.assertSimple()
    assert len(g.disjointPartitions()) == 4
    assert len(g.disjointPartitions(verts[1:])) == 4
    assert len(g.disjointPartitions(verts[2:])) == 3
    assert g.connectedComponent(verts[-1]) == set(verts[-1:])
    assert g.connectedComponent(verts[1], verts[1:]) == set(verts[1:2])
    backbone = [list(p)[0] for p in g.disjointPartitions()]
    for i in range(len(backbone) - 1):
        g.addEdge(backbone[i], backbone[i + 1])
    g.addEdge(backbone[0], backbone[-1])
    assert len(g.disjointPartitions()) == 1
    assert g.connectedComponent(verts[0]) == set(verts)
    assert g.connected(verts[0], verts[-1])
    assert g.isConnectedSet(set(verts[:1] + verts[-1:]))
    assert g.edgeCount(without={3, 6}) == g.edgeCount() - 5
    assert g.edgeCount(without={0, 9}) == g.edgeCount() - 4


def _testReducedGraph():
    og = _build4by4()
    g = OnlineReducedGraph(og)
    for v in g.vertices:
        assert g.adjacencies(v) == og.adjacencies(v)
    c = list(g.components.keys())[0]
    assert g.componentDeleted is None
    assert g.componentReduced is None
    assert g.newSubComponents is None
    assert g.separatorsChanged is False
    assert g.allMasked is False
    assert g.disjoint is False
    assert g.vertices == set(range(16))
    assert len(g.components) == 1
    assert g.edgeCount() == 24
    for v in [5, 6, 9, 10]:
        g.maskVertex(v)
        assert g.separatorsChanged is False
        assert len(g.components) == 1
        assert c in g.components
        assert g.componentReduced == c
    assert g.sortClosest([1, 2, 3], 11) == [3, 2, 1]
    g.maskVertex(7)
    assert g.sortClosest([1, 2, 3], 11) == [1, 2, 3]
    assert g.separatorsChanged is True
    assert len(g.components) == 1
    assert c in g.components
    assert g.componentDeleted is None
    g.maskVertex(13)
    assert g.sortClosest([1, 2, 3], 11) == []
    assert g.separatorsChanged is True
    assert len(g.components) == 2
    assert g.newSubComponents == set(g.components.keys())
    assert g.componentDeleted == c
    assert g.disjoint is True


def _equalSetSets(sets_a, sets_b):
    sets_a = set(frozenset(s) for s in sets_a)
    sets_b = set(frozenset(s) for s in sets_b)
    if sets_a != sets_b:
        print(str(len(sets_a)) + " != " + str(len(sets_b)))
    return sets_a == sets_b


def _testGraphBiconnected():
    random.seed('consistent seed')
    edgesets = 3 * [
        {0: set(), 2: {3, 13}, 3: {2, 4, 14}, 4: {3, 15},
         13: {2, 14}, 14: {25, 3, 13, 15}, 15: {4, 14},
         17: {18, 28}, 18: {17, 29}, 22: {23},
         23: {34, 22}, 25: {36, 14}, 28: {17, 29, 39},
         29: {18, 28}, 34: {35, 45, 23}, 35: {34, 36},
         36: {25, 35, 37, 47}, 37: {36, 38}, 38: {37, 39},
         39: {28, 38}, 42: {119}, 44: {45}, 45: {34, 44},
         47: {58, 36}, 52: {120, 63}, 54: {120, 65},
         57: {58, 68}, 58: {57, 59, 47}, 59: {58, 70},
         63: {52, 118}, 65: {118, 54}, 66: {77},
         68: {57, 79}, 70: {81, 59}, 72: set(), 75: {117},
         77: {66}, 79: {80, 68}, 80: {81, 91, 79},
         81: {80, 70}, 84: {95}, 91: {80, 102},
         94: {105, 95}, 95: {96, 106, 84, 94}, 96: {95},
         99: {100}, 100: {99, 111}, 102: {91},
         104: {105, 115}, 105: {104, 106, 116, 94},
         106: {105, 95}, 111: {100}, 115: {104, 116},
         116: {105, 115}, 117: {75, 119}, 118: {65, 63},
         119: {42, 117}, 120: {52, 54}},

        {2: {3}, 3: {2, 4, 10}, 4: {3}, 10: {17, 3},
         14: {21}, 16: {17, 23}, 17: {16, 24, 10, 18},
         18: {17, 25}, 20: {27}, 21: {28, 22, 14},
         22: {21, 23}, 23: {16, 24, 30, 22},
         24: {17, 31, 25, 23}, 25: {24, 32, 18, 26},
         26: {25, 27}, 27: {26, 20, 34}, 28: {21},
         30: {31, 23}, 31: {24, 32, 38, 30}, 32: {25, 31},
         34: {27}, 38: {45, 31}, 44: {45},
         45: {44, 46, 38}, 46: {45}},

        {20: {31}, 24: {35}, 31: {42, 20}, 34: {35, 45},
         35: {24, 34, 46}, 39: {40}, 40: {41, 51, 39},
         41: {40, 42, 52}, 42: {41, 53, 31}, 44: {45, 55},
         45: {56, 34, 44, 46}, 46: {57, 35, 45},
         51: {40, 52, 62}, 52: {41, 51, 53, 63},
         53: {64, 42, 52}, 55: {56, 66, 44},
         56: {57, 67, 45, 55}, 57: {56, 68, 46},
         62: {73, 51, 63}, 63: {64, 74, 52, 62}, 64: {53, 63},
         66: {67, 55}, 67: {56, 66, 68, 78},
         68: {57, 67, 69, 79}, 69: {80, 68}, 72: {73, 83},
         73: {72, 74, 62}, 74: {73, 63}, 78: {67, 79},
         79: {80, 90, 68, 78}, 80: {81, 91, 69, 79},
         81: {80, 82, 92}, 82: {81, 83}, 83: {72, 82},
         90: {91, 79}, 91: {80, 90, 92}, 92: {81, 91}}]
    for es in edgesets:
        es = deepcopy(es)
        g = SimpleGraph(es)
        g2 = SimpleGraph(g)
        assert set(g.vertices) == set(g2.vertices)
        g2.removeVertex(list(g2.vertices)[0])
        assert set(g.vertices) != set(g2.vertices)
        verts = set(g.vertices)
        vertlist = list(verts)
        random.shuffle(vertlist)
        rgstack = [OnlineReducedGraph(QueryableSimpleGraph(deepcopy(es)))]
        for v in vertlist:
            rgstack.append(rgstack[-1].copy())
            rgstack[-1].maskVertex(v)
        while vertlist:
            assert set(es) == verts
            bcs, seps = g.biconnectedComponents()
            for bc1, bc2 in combinations(bcs, 2):
                assert len(bc1 & bc2) < 2
                assert not bc1.issubset(bc2)
                assert not bc2.issubset(bc1)

            rg = rgstack.pop(0)
            # noinspection PyProtectedMember
            rg._assertValidState()
            rg_bcs, rg_seps = rg.biconnectedComponents()
            assert _equalSetSets(bcs, rg_bcs)
            assert seps == rg_seps

            assert reduce(set.union, bcs) == verts
            innerbcs = [bc - seps for bc in bcs]
            assert sum(map(len, innerbcs)) + len(seps) == len(verts)
            memberbcs = dict((v, set()) for v in verts)
            for i, bc in enumerate(bcs):
                for v in bc:
                    memberbcs[v].add(i)
            parts = g.disjointPartitions()
            assert _equalSetSets(parts, rg.disjointPartitions())
            for part in parts:
                for v in part:
                    assert rg.connectedComponent(v) == part
            for v in verts:
                novparts = g.disjointPartitions(verts - {v})
                if g.isSeparator(v):
                    assert rg.isSeparator(v)
                    assert v in seps
                    assert len(memberbcs[v]) > 1
                    assert len(novparts) == len(parts) + len(memberbcs[v]) - 1
                else:
                    assert not rg.isSeparator(v)
                    assert v not in seps
                    assert len(memberbcs[v]) == 1
                    if len(g.connectedComponent(v)) == 1:
                        assert len(novparts) == len(parts) - 1
                    else:
                        assert len(novparts) == len(parts)
            for bc in bcs:
                bcs_, seps_ = g.biconnectedComponents(bc)
                assert len(bcs_) == 1
                assert bcs_[0] == bc
                assert not seps_
                for v in bc:
                    assert bc.issubset(g.connectedComponent(v))
                    assert bc == g.connectedComponent(v, bc)
            v = vertlist.pop(0)
            verts.remove(v)
            g.removeVertex(v)


def _build4by4():
    # makes a grid structure like:
    # 0 - 1 - 2 - 3
    # !   !   !   !
    # 4 - 5 - 6 - 7
    # !   !   !   !
    # 8 - 9 - 10- 11
    # !   !   !   !
    # 12- 13- 14- 15
    g = SimpleGraph()
    g.addVertices(range(16))
    for k in range(0, 16, 4):
        for i in range(k, k + 3):
            g.addEdge(i, i + 1)
    for k in range(4):
        for i in range(k, 12, 4):
            g.addEdge(i, i + 4)
    for i in [0, 3, 12, 15]:
        assert g.degree(i) == 2
    for i in [1, 2, 7, 11, 14, 13, 8, 4]:
        assert g.degree(i) == 3
    for i in [5, 6, 9, 10]:
        assert g.degree(i) == 4
    return g


def _testSortClosest():
    g = _build4by4()
    assert g.sortClosest([], 0) == []
    verts = [5, 1, 0, 7, 14, 15]
    assert g.sortClosest(verts, 5) == verts
    verts = [15, 11, 7, 3]
    assert g.sortClosest(verts, 13) == verts
    verts = [13, 14, 15]
    assert g.sortClosest(verts, 8) == verts

    mask = set(g.vertices)
    mask.remove(13)
    mask.remove(14)
    assert g.sortClosest(verts, 8, mask) == [15]
    mask.remove(10)
    mask.remove(7)
    assert g.sortClosest(verts, 8, mask) == []

    g.removeVertices([9, 12, 6])
    verts.reverse()
    assert g.sortClosest(verts, 8) == verts
    g.removeVertex(2)
    assert g.sortClosest(verts, 8) == []


def _testShortestPath():
    g = _build4by4()
    assert g.shortestPath(0, 12) == [0, 4, 8, 12]
    assert g.shortestPath(12, 0) == [12, 8, 4, 0]
    assert g.shortestPath(1, 9) == [1, 5, 9]
    g.removeVertices([4, 5, 6])
    assert g.shortestPath(1, 9) == [1, 2, 3, 7, 11, 10, 9]
    v_a = g.pushVertex()
    g.addEdge(v_a, 2)
    g.addEdge(v_a, 10)
    assert g.shortestPath(1, 9) == [1, 2, v_a, 10, 9]
    v_b = g.pushVertex()
    g.addEdge(v_b, 3)
    g.addEdge(v_b, 15)
    assert g.shortestPath(1, 15) == [1, 2, 3, v_b, 15]
    assert g.shortestPath(15, 2) == [15, v_b, 3, 2]
    g.removeVertices([v_a, v_b, 13])
    assert g.shortestPath(8, 14) == [8, 9, 10, 14]
    g.removeVertex(10)
    assert g.shortestPath(8, 14) == []
    v_c = g.pushVertex()
    g.addEdge(v_c, 9)
    g.addEdge(v_c, 2)
    assert g.shortestPath(8, 14) == [8, 9, v_c, 2, 3, 7, 11, 15, 14]
    v_d = g.pushVertex()
    g.addEdge(v_d, v_c)
    g.addEdge(v_d, 11)
    assert g.shortestPath(8, 14) == [8, 9, v_c, v_d, 11, 15, 14]

    g = OnlineReducedGraph(_build4by4())
    assert g.shortestPath(1, 9) == [1, 5, 9]
    g.maskVertex(4)
    g.maskVertex(5)
    g.maskVertex(6)
    assert g.shortestPath(1, 9) == [1, 2, 3, 7, 11, 10, 9]
    g.maskVertex(13)
    assert g.shortestPath(8, 14) == [8, 9, 10, 14]
    g.maskVertex(10)
    assert g.shortestPath(8, 14) == []


def _testEccentricity():
    g = _build4by4()
    for v in g.vertices:
        if g.degree(v) == 2:
            assert g.eccentricity(v) == 6
        elif g.degree(v) == 4:
            assert g.eccentricity(v) == 4
        else:
            assert g.degree(v) == 3
            assert g.eccentricity(v) == 5
    v_a = g.pushVertex()
    assert g.eccentricity(v_a) == 0
    v_b = g.pushVertex()
    g.addEdge(v_a, v_b)
    assert g.eccentricity(v_a) == 1
    g.addEdge(v_a, 7)
    assert g.eccentricity(v_a) == 6
    assert g.eccentricity(v_b) == g.eccentricity(v_a) + 1
    assert g.eccentricity(12) == 7
    g.addEdge(v_b, 15)
    assert g.eccentricity(12) == 6
    mask = set(g.vertices) - {13, 9}
    assert g.eccentricity(12, mask) == 7
    g.removeEdge(v_a, 7)
    assert g.eccentricity(12, mask) == 9


if __name__ == '__main__':
    _testGraph()
    _testReducedGraph()
    _testGraphBiconnected()
    _testSortClosest()
    _testShortestPath()
    _testEccentricity()
    print("Tests passed.")
    exit(0)
