#!/usr/bin/env python

import random
from copy import deepcopy
from itertools import combinations
from graph import SimpleGraph, QueryableSimpleGraph, OnlineReducedGraph


def _checkOnlineReducedGraph(rg):
    assert rg._vertices == set(rg._biconComponentMap)
    componentSum = set()
    for k, c in rg._components.iteritems():
        assert c
        assert not c & componentSum
        componentSum |= c
    assert rg._vertices == componentSum
    for v, kset in rg._biconComponentMap.iteritems():
        assert kset
        assert (len(kset) > 1) == (v in rg._separators)
        for k in kset:
            assert v in rg._biconComponents[k]
    assert set(rg._separatorMap) == set(rg._biconComponents)
    for k, vset in rg._separatorMap.iteritems():
        assert vset == rg._separators & rg._biconComponents[k]
    for bc1, bc2 in combinations(rg._biconComponents.values(), 2):
        assert len(bc1 & bc2) < 2
        assert not bc1.issubset(bc2)
        assert not bc2.issubset(bc1)
    bcs, seps = rg._graph.biconnectedComponents(rg._vertices)
    assert seps == rg._separators
    assert len(bcs) == len(rg._biconComponents)
    for k, bc in rg._biconComponents.iteritems():
        assert bc
        bcs, seps = rg._graph.biconnectedComponents(bc)
        assert len(bcs) == 1 and not seps
        for v, kset in rg._biconComponentMap.iteritems():
            assert (k in kset) == (v in bc)


def _testGraph():
    g = SimpleGraph()
    assert isinstance(g, QueryableSimpleGraph)
    assert not isinstance(g.asReadOnly(), SimpleGraph)
    assert isinstance(g.asReadOnly(), QueryableSimpleGraph)
    g.assertSimple()
    verts = []
    for i in xrange(10):
        verts.append(g.pushVertex())
    assert len(set(verts)) == len(verts)
    for v in verts:
        assert not g.adjacencies(v)
        assert g.connectedComponent(v) == set([v])
        assert not g.isSeparator(v)
        assert g.isConnectedSet([v])
    parts = g.disjointPartitions()
    assert len(parts) == len(verts)
    s = set()
    for p in parts:
        assert len(p) == 1
        s.add(p.pop())
    assert s == set(verts)
    for i in xrange(len(verts) - 1):
        g.addEdge(verts[i], verts[i + 1])
        for v in verts[i + 2:]:
            assert not g.connected(verts[i + 1], v)
            assert not g.connected(v, verts[i + 1])
        for j in xrange(i + 1):
            if j > 0:
                assert g.connected(verts[0], verts[j])
                assert g.connected(verts[j], verts[0])
            assert g.connectedComponent(verts[j]) == set(verts[:i + 2])
    for v in verts:
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
    g.addEdge(verts[0], shortcut)
    g.addEdge(verts[-1], shortcut)
    assert g.shortestPath(verts[0], verts[-1]) == \
        [verts[0], shortcut, verts[-1]]

    assert verts[0] == 0
    g.removeEdge(verts[-1], shortcut)
    assert g.shortestPath(shortcut, verts[1]) == [shortcut, verts[0], verts[1]]
    g.removeVertex(shortcut)

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
            assert g.shortestPath(v1, v2, mask) is None
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
    for i in xrange(len(backbone) - 1):
        g.addEdge(backbone[i], backbone[i + 1])
    g.addEdge(backbone[0], backbone[-1])
    assert len(g.disjointPartitions()) == 1
    assert g.connectedComponent(verts[0]) == set(verts)
    assert g.connected(verts[0], verts[-1])
    assert g.isConnectedSet(set(verts[:1] + verts[-1:]))


def _equalSetSets(sets_a, sets_b):
    sets_a = set(frozenset(s) for s in sets_a)
    sets_b = set(frozenset(s) for s in sets_b)
    if sets_a != sets_b:
        print len(sets_a), "!=", len(sets_b)
    return sets_a == sets_b


def _testGraphBiconnected():
    random.seed('consistent seed')
    edgesets = 3 * [\
        {0: set([]), 2: set([3, 13]), 3: set([2, 4, 14]), 4: set([3, 15]), \
        13: set([2, 14]), 14: set([25, 3, 13, 15]), 15: set([4, 14]), \
        17: set([18, 28]), 18: set([17, 29]), 22: set([23]), \
        23: set([34, 22]), 25: set([36, 14]), 28: set([17, 29, 39]), \
        29: set([18, 28]), 34: set([35, 45, 23]), 35: set([34, 36]), \
        36: set([25, 35, 37, 47]), 37: set([36, 38]), 38: set([37, 39]), \
        39: set([28, 38]), 42: set([119]), 44: set([45]), 45: set([34, 44]), \
        47: set([58, 36]), 52: set([120, 63]), 54: set([120, 65]), \
        57: set([58, 68]), 58: set([57, 59, 47]), 59: set([58, 70]), \
        63: set([52, 118]), 65: set([118, 54]), 66: set([77]), \
        68: set([57, 79]), 70: set([81, 59]), 72: set([]), 75: set([117]), \
        77: set([66]), 79: set([80, 68]), 80: set([81, 91, 79]), \
        81: set([80, 70]), 84: set([95]), 91: set([80, 102]), \
        94: set([105, 95]), 95: set([96, 106, 84, 94]), 96: set([95]), \
        99: set([100]), 100: set([99, 111]), 102: set([91]), \
        104: set([105, 115]), 105: set([104, 106, 116, 94]), \
        106: set([105, 95]), 111: set([100]), 115: set([104, 116]), \
        116: set([105, 115]), 117: set([75, 119]), 118: set([65, 63]), \
        119: set([42, 117]), 120: set([52, 54])},

        {2: set([3]), 3: set([2, 4, 10]), 4: set([3]), 10: set([17, 3]), \
        14: set([21]), 16: set([17, 23]), 17: set([16, 24, 10, 18]), \
        18: set([17, 25]), 20: set([27]), 21: set([28, 22, 14]), \
        22: set([21, 23]), 23: set([16, 24, 30, 22]), \
        24: set([17, 31, 25, 23]), 25: set([24, 32, 18, 26]), \
        26: set([25, 27]), 27: set([26, 20, 34]), 28: set([21]), \
        30: set([31, 23]), 31: set([24, 32, 38, 30]), 32: set([25, 31]), \
        34: set([27]), 38: set([45, 31]), 44: set([45]), \
        45: set([44, 46, 38]), 46: set([45])},

        {20: set([31]), 24: set([35]), 31: set([42, 20]), 34: set([35, 45]), \
        35: set([24, 34, 46]), 39: set([40]), 40: set([41, 51, 39]), \
        41: set([40, 42, 52]), 42: set([41, 53, 31]), 44: set([45, 55]), \
        45: set([56, 34, 44, 46]), 46: set([57, 35, 45]), \
        51: set([40, 52, 62]), 52: set([41, 51, 53, 63]), \
        53: set([64, 42, 52]), 55: set([56, 66, 44]), \
        56: set([57, 67, 45, 55]), 57: set([56, 68, 46]), \
        62: set([73, 51, 63]), 63: set([64, 74, 52, 62]), 64: set([53, 63]), \
        66: set([67, 55]), 67: set([56, 66, 68, 78]), \
        68: set([57, 67, 69, 79]), 69: set([80, 68]), 72: set([73, 83]), \
        73: set([72, 74, 62]), 74: set([73, 63]), 78: set([67, 79]), \
        79: set([80, 90, 68, 78]), 80: set([81, 91, 69, 79]), \
        81: set([80, 82, 92]), 82: set([81, 83]), 83: set([72, 82]), \
        90: set([91, 79]), 91: set([80, 90, 92]), 92: set([81, 91])}]
    for es in edgesets:
        es = deepcopy(es)
        g = SimpleGraph(es)
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
            _checkOnlineReducedGraph(rg)
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
                novparts = g.disjointPartitions(verts - set([v]))
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


if __name__ == '__main__':
    _testGraph()
    _testGraphBiconnected()
    print "Tests passed."
    exit(0)
