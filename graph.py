#!/usr/bin/env python

from collections import deque
from itertools import izip, combinations, count


class QueryableSimpleGraph(object):
    def __init__(self, edgeSets):
        self._edges = edgeSets
        # vertex : set of connected vertices (doubly-linked)
        # keys are vertex collection (isolated vertices have empty set)

        for v, adj in edgeSets.iteritems():
            assert v not in adj
            for u in adj:
                assert u in edgeSets
                assert v in edgeSets[u]

    @property
    def vertices(self):
        return iter(self._edges)

    def copyEdgeSets(self):
        return dict((v, adj.copy()) for v, adj in self._edges.iteritems())

    def adjacent(self, v1, v2):
        """Return True iff v1 and v2 share an edge."""
        return v2 in self._edges[v1]

    def adjacencies(self, v, mask=None):
        """
            Return set of vertices adjacent to v. Never includes v.
            mask: use only these vertices and their incident edges
        """
        if mask is None:
            return self._edges[v].copy()
        else:
            return self._edges[v].intersection(mask)

    def connected(self, v1, v2, mask=None):
        """
            Return True iff there is some path from v1 to v2.
            mask: use only these vertices and their incident edges
        """
        assert v1 != v2
        if self.adjacent(v1, v2):
            return True
        toVisit = self._maskVertices(mask)
        front1, front2 = set([v1]), set([v2])
        while front1:
            toVisit -= front1
            front1 = reduce(set.union, \
                (self.adjacencies(v, toVisit) for v in front1))
            if front1.intersection(front2):
                return True
            front1, front2 = front2, front1
        return False

    def shortestPath(self, v1, v2, mask=None):
        """
            Return a minimal list of vertices connecting v1 to v2.
                path[0] == v1, path[-1] == v2
            Return None if not connected.
            mask: use only these vertices and their incident edges
        """
        if v1 == v2:
            return [v1]
        elif self.adjacent(v1, v2):
            return [v1, v2]
        mask_a = self._maskVertices(mask)
        mask_a.discard(v1)
        mask_a.discard(v2)
        mask_b = mask_a.copy()
        trees = {v1: None, v2: None}  # vertex: parent
        leafs_a, leafs_b = set([v1]), set([v2])
        join = None
        while mask_a and join is None:
            leafs = set()
            while leafs_a:
                v = leafs_a.pop()
                ext = self.adjacencies(v, mask_a)
                mask_a -= ext
                leafs |= ext
                for v_ext in ext:
                    if v_ext in leafs_b:
                        join = (v_ext, v)
                        break
                    trees[v_ext] = v
                else:
                    continue
                break
            if not leafs:
                break
            leafs_a, leafs_b = leafs_b, leafs
            mask_a, mask_b = mask_b, mask_a
        if join is None:
            return None
        path1, path2 = [join[0]], [join[1]]
        for path in (path1, path2):
            while trees[path[-1]] is not None:
                path.append(trees[path[-1]])
        if path1[-1] == v2:
            path1, path2 = path2, path1
        path1.reverse()
        path1.extend(path2)
        return path1

    def isConnectedSet(self, vertices, mask=None):
        """
            Return True iff all pairs from 'vertices' are connected.
            mask: use only these vertices and their incident edges
        """
        if len(vertices) == 1:
            return True
        elif len(vertices) == 2:
            it = iter(vertices)
            return self.connected(next(it), next(it), mask)
        toVisit = self._maskVertices(mask)
        toVisit.update(vertices)
        fronts = deque(set([v]) for v in vertices)
        while len(fronts) > 1:
            front = fronts.popleft()
            joined = False
            for joinfront in fronts:
                if front.intersection(joinfront):
                    joinfront |= front
                    joined = True
            if joined:
                continue
            toVisit -= front
            front = reduce(set.union, \
                (self.adjacencies(v, toVisit) for v in front))
            if not front:
                return False
            fronts.append(front)
        return True

    def isSeparator(self, v, mask=None):
        """
            Return True iff removing v will divide v's connected component.
            mask: use only these vertices and their incident edges
        """
        mask = self._maskVertices(mask)
        links = self.adjacencies(v, mask)
        if len(links) < 2:
            return False
        mask.discard(v)
        return not self.isConnectedSet(links, mask)

    def biconnectedComponents(self, mask=None):
        """
            Return tuple(list(sets), set) containing the sets of vertices
            in biconnected components and the set of articulation points.
            mask: use only these vertices and their incident edges
        """
        vertices = self._maskVertices(mask)
        subtrees = dict((v, set([v])) for v in vertices)
        adjs = dict((v, self._edges[v] & vertices) for v in vertices)
        components = []
        separators = set()
        toVisit = vertices.copy()
        while toVisit:
            root = toVisit.pop()
            stack = [root]
            depth = {root: 0}
            lowpoint = {root: 0}
            v_child = None
            while stack:
                v = stack[-1]

                adj = adjs[v]
                v_next = None
                while v_next is None and adj:
                    v_next = adj.pop()
                    if v_next not in toVisit:
                        v_next = None

                if v_next is None:
                    stack.pop()
                    v_parent = stack[-1] if stack else None
                    for v_adj in self.adjacencies(v, vertices):
                        if v_adj != v_parent:
                            lowpoint[v] = min(lowpoint[v], depth[v_adj])
                else:
                    lowpoint[v_next] = depth[v_next] = len(stack)
                    toVisit.remove(v_next)
                    stack.append(v_next)

                if v_child is not None:
                    lowpoint[v] = min(lowpoint[v], lowpoint[v_child])
                    if stack and lowpoint[v_child] >= depth[v]:
                        separators.add(v)
                        c = subtrees[v_child]
                        c.add(v)
                        components.append(c)
                    else:
                        subtrees[v] |= subtrees[v_child]
                    del subtrees[v_child]

                v_child = v if v_next is None else None

            components.append(subtrees[root])
            del subtrees[root]
        assert not subtrees
        return (components, separators)

    def connectedComponent(self, v, mask=None):
        """
            Return set of vertices connected by some path to v (including v).
            mask: use only these vertices and their incident edges
        """
        toVisit = self._maskVertices(mask)
        toVisit.add(v)
        component = set([v])
        stack = [v]
        while stack:
            v = stack.pop()
            ext = self.adjacencies(v, toVisit)
            toVisit -= ext
            component |= ext
            stack.extend(ext)
        return component

    def disjointPartitions(self, mask=None):
        """
            Return list of sets of vertices such that:
                All vertices in each set are connected.
                No two sets are connected to each other.
            mask: use only these vertices and their incident edges
        """
        toVisit = self._maskVertices(mask)
        partitions = []
        while toVisit:
            p = self.connectedComponent(toVisit.pop(), toVisit)
            toVisit -= p
            partitions.append(p)
        return partitions

    def _maskVertices(self, mask=None):
        """
            Return a new set containing the graph's vertices.
            mask: use only these vertices, or all vertices if None
        """
        return set(self._edges if mask is None else mask)


class SimpleGraph(QueryableSimpleGraph):
    def __init__(self, edgeSets=None):
        super(SimpleGraph, self).__init__(edgeSets or {})

    def asReadOnly(self):
        """Return a read-only interface to this instance."""
        return QueryableSimpleGraph(self._edges)

    def pushVertex(self):
        """Return new vertex id."""
        v = max(self._edges) + 1 if self._edges else 0
        self._edges[v] = set()
        return v

    def removeVertex(self, v):
        """Delete a vertex and any incident edges."""
        for adj in self._edges[v]:
            self._edges[adj].remove(v)
        del self._edges[v]

    def addEdge(self, v1, v2):
        """Connect v1 and v2. Error if loop or already connected."""
        assert v1 != v2
        assert v2 not in self._edges[v1]
        self._edges[v1].add(v2)
        self._edges[v2].add(v1)

    def removeEdge(self, v1, v2):
        """Delete edge between v1 and v2. Error if no such edge."""
        assert v1 != v2
        self._edges[v1].remove(v2)
        self._edges[v2].remove(v1)


class OnlineReducedGraph(object):
    def __init__(self, graph, state=None):
        self._graph = graph
        if state is None:
            self._initializeState()
        else:
            self._keys, \
            self._vertices, \
            self._components, \
            self._biconComponents, \
            self._separators, \
            self._componentMap, \
            self._biconComponentMap, \
            self._separatorMap = state

    def copy(self):
        return OnlineReducedGraph(self._graph, (\
            self._keys, \
            self._vertices, \
            self._components, \
            self._biconComponents, \
            self._separators, \
            self._componentMap, \
            self._biconComponentMap, \
            self._separatorMap))

    def maskVertex(self, v):
        self._vertices = self._vertices.copy()
        self._vertices.remove(v)
        # self._vertices valid

        self._components = self._components.copy()
        self._componentMap = self._componentMap.copy()
        c_k = self._componentMap.pop(v)
        c_k_deleted = None
        c_k_reduced = None
        c_kset_new = None
        c = self._components[c_k]
        if len(c) == 1:
            c_k_deleted = c_k
            del self._components[c_k]
        else:
            c = c.copy()
            c.remove(v)
            if v in self._separators:
                c_k_deleted = c_k
                del self._components[c_k]
                c_kset_new = set()
                for c_new in self._graph.disjointPartitions(c):
                    c_k_new = next(self._keys)
                    self._components[c_k_new] = c_new
                    for cv in c_new:
                        assert self._componentMap[cv] != c_k_new
                        self._componentMap[cv] = c_k_new
                    c_kset_new.add(c_k_new)
                assert len(c_kset_new) > 1
            else:
                c_k_reduced = c_k
                self._components[c_k] = c
        # self._components valid
        # self._componentMap valid

        self._biconComponents = self._biconComponents.copy()
        self._biconComponentMap = self._biconComponentMap.copy()
        bc_kset = self._biconComponentMap.pop(v)
        biconReduce = []
        if c_k_deleted:
            if c_kset_new:
                assert len(bc_kset) > 1
                for bc_k in bc_kset:
                    biconReduce.append(\
                        (bc_k, self._biconComponents[bc_k].copy()))
            else:
                assert len(bc_kset) == 1
                bc_k = next(iter(bc_kset))
                assert len(self._biconComponents[bc_k]) == 1
                del self._biconComponents[bc_k]
                assert v not in self._separators
                assert len(self._separatorMap[bc_k]) == 0
                self._separatorMap = self._separatorMap.copy()
                del self._separatorMap[bc_k]
        else:
            assert c_k_reduced
            assert v not in self._separators
            assert len(bc_kset) == 1
            bc_k = next(iter(bc_kset))
            biconReduce.append((bc_k, self._biconComponents[bc_k].copy()))

        if biconReduce:
            self._separators = self._separators.copy()
            self._separators.discard(v)
            self._separatorMap = self._separatorMap.copy()
            while biconReduce:
                bc_k, bc_reduced = biconReduce.pop()
                bc_reduced.remove(v)
                if len(bc_reduced) == 1:
                    other = next(iter(bc_reduced))
                    bc_kset_other = self._biconComponentMap[other]
                    if len(bc_kset_other) > 1:
                        bc_kset_other = self._biconComponentMap[other].copy()
                        bc_kset_other.remove(bc_k)
                        self._biconComponentMap[other] = bc_kset_other
                        del self._biconComponents[bc_k]
                        del self._separatorMap[bc_k]
                        if len(bc_kset_other) == 1:
                            self._separators.remove(other)
                            bc_k_other = next(iter(bc_kset_other))
                            m = self._separatorMap[bc_k_other].copy()
                            m.remove(other)
                            self._separatorMap[bc_k_other] = m
                        continue
                bcs, seps = self._graph.biconnectedComponents(bc_reduced)
                if seps:
                    del self._biconComponents[bc_k]
                    for bcv in bc_reduced:
                        ks = self._biconComponentMap[bcv].copy()
                        ks.remove(bc_k)
                        self._biconComponentMap[bcv] = ks
                    oldseps = self._separatorMap.pop(bc_k)
                    for newbc_k, newbc in izip(self._keys, bcs):
                        self._biconComponents[newbc_k] = newbc
                        self._separatorMap[newbc_k] = newbc & (oldseps | seps)
                        for bcv in newbc:
                            self._biconComponentMap[bcv].add(newbc_k)
                    self._separators = self._separators | seps
                else:
                    self._biconComponents[bc_k] = bc_reduced
                    seps = self._separatorMap[bc_k]
                    if v in seps:
                        seps = seps.copy()
                        seps.remove(v)
                        self._separatorMap[bc_k] = seps

    def isSeparator(self, v):
        return v in self._separators

    def biconnectedComponents(self):
        return (self._biconComponents.values(), self._separators)

    def connectedComponent(self, v):
        return self._components[self._componentMap[v]]

    def disjointPartitions(self):
        return self._components.values()

    def assertIntegrity(self):
        assert self._vertices == set(self._componentMap)
        assert self._vertices == set(self._biconComponentMap)
        componentSum = set()
        for k, c in self._components.iteritems():
            assert c
            for v in c:
                assert self._componentMap[v] == k
            assert not c & componentSum
            componentSum |= c
        assert self._vertices == componentSum
        for v, kset in self._biconComponentMap.iteritems():
            assert kset
            assert (len(kset) > 1) == (v in self._separators)
            for k in kset:
                assert v in self._biconComponents[k]
        assert set(self._separatorMap) == set(self._biconComponents)
        for k, vset in self._separatorMap.iteritems():
            assert vset == self._separators & self._biconComponents[k]
        for bc1, bc2 in combinations(self._biconComponents.values(), 2):
            assert len(bc1 & bc2) < 2
            assert not bc1.issubset(bc2)
            assert not bc2.issubset(bc1)
        bcs, seps = self._graph.biconnectedComponents(self._vertices)
        assert seps == self._separators
        assert len(bcs) == len(self._biconComponents)
        for k, bc in self._biconComponents.iteritems():
            assert bc
            bcs, seps = self._graph.biconnectedComponents(bc)
            assert len(bcs) == 1 and not seps
            for v, kset in self._biconComponentMap.iteritems():
                assert (k in kset) == (v in bc)

    def _initializeState(self):
        # self._vertices           set of unmasked vertices
        # self._components         key: set of vertices
        # self._biconComponents    key: set of vertices
        # self._separators         set of vertices
        # self._componentMap       v: component key
        # self._biconComponentMap  v: set of bicon component keys
        # self._separatorMap       bicon component key: set of separators

        self._keys = count(1)

        self._vertices = set(self._graph.vertices)
        self._components = \
            dict(izip(self._keys, self._graph.disjointPartitions()))

        bcs, seps = self._graph.biconnectedComponents()
        self._biconComponents = dict(izip(self._keys, bcs))
        self._separators = seps

        self._componentMap = \
            dict((v, k) for k, c in self._components.iteritems() for v in c)

        self._biconComponentMap = dict((v, set()) for v in self._vertices)
        self._separatorMap = dict((k, set()) for k in self._biconComponents)
        for k, bc in self._biconComponents.iteritems():
            for v in bc:
                self._biconComponentMap[v].add(k)
                if v in self._separators:
                    self._separatorMap[k].add(v)


def _testGraph():
    g = SimpleGraph()
    assert isinstance(g, QueryableSimpleGraph)
    assert not isinstance(g.asReadOnly(), SimpleGraph)
    assert isinstance(g.asReadOnly(), QueryableSimpleGraph)
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
    import random
    from copy import deepcopy
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
            rg.assertIntegrity()
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
