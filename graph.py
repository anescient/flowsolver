#!/usr/bin/env python


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
        if v2 in self._edges[v1]:
            return True
        toVisit = self._maskVertices(mask)
        toVisit.discard(v1)
        toVisit.discard(v2)
        front1 = self.adjacencies(v1, toVisit)
        front2 = self.adjacencies(v2, toVisit)
        if not front1 or not front2:
            return False
        flip = False
        while not front1.intersection(front2):
            if flip:
                toVisit -= front1
                front1 = set.union(\
                    *(self.adjacencies(fv, toVisit) for fv in front1))
                if not front1:
                    return False
            else:
                toVisit -= front2
                front2 = set.union(\
                    *(self.adjacencies(fv, toVisit) for fv in front2))
                if not front2:
                    return False
            flip = not flip
        return True

    def isConnectedSet(self, vset, mask=None):
        """
            Return True iff all vertices in vset are connected.
            mask: use only these vertices and their incident edges
        """
        if len(vset) == 1:
            return True
        elif len(vset) == 2:
            it = iter(vset)
            return self.connected(next(it), next(it), mask)
        toVisit = self._maskVertices(mask)
        toVisit |= vset
        fronts = [self.adjacencies(v, toVisit) for v in vset]
        if not all(fronts):
            return False
        toVisit -= vset
        while len(fronts) > 1:
            front = fronts.pop(0)
            joined = False
            for joinfront in fronts:
                if front.intersection(joinfront):
                    joinfront |= front
                    joined = True
            if joined:
                continue
            toVisit -= front
            front = set.union(\
                *(self.adjacencies(fv, toVisit) for fv in front))
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
        toVisit = vertices.copy()
        subtrees = dict((v, set([v])) for v in toVisit)
        components = []
        separators = set()
        while toVisit:
            root = toVisit.pop()
            stack = [root]
            depth = {root: 0}
            lowpoint = {root: 0}
            v_child = None
            while stack:
                v = stack[-1]
                v_next = next(iter(self.adjacencies(v, toVisit)), None)
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
        assert len(subtrees) == 0
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
        assert len(g.adjacencies(v)) == 0
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
        for j in xrange(i + 1):
            if j > 0:
                assert g.connected(verts[0], verts[j])
            assert g.connectedComponent(verts[j]) == set(verts[:i + 2])
    for v in verts:
        assert g.connectedComponent(v) == set(verts)
    assert not g.isSeparator(verts[0])
    assert not g.isSeparator(verts[-1])
    assert all(g.isSeparator(v) for v in verts[1:-1])
    g.addEdge(verts[0], verts[-1])
    assert not any(g.isSeparator(v) for v in verts)
    g.removeEdge(verts[0], verts[-1])
    g.asReadOnly()
    parts = g.disjointPartitions(verts[:2] + verts[3:])
    assert len(parts) == 2
    assert len(parts[0].intersection(parts[1])) == 0
    assert g.isConnectedSet(parts[0])
    assert g.isConnectedSet(parts[1])
    assert not g.isConnectedSet(set(verts))
    assert verts[2] not in parts[0].union(parts[1])
    assert parts[0].union(parts[1]) == set(verts) - set(verts[2:3])
    drops = [verts[i] for i in [2, 5, 8]]
    for v in drops:
        g.removeVertex(v)
        verts.remove(v)
    assert len(g.adjacencies(verts[-1])) == 0
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


def _testGraphBiconnected():
    edgesets = [{\
        0: set([]), 2: set([3, 13]), 3: set([2, 4, 14]), 4: set([3, 15]), \
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
        45: set([44, 46, 38]), 46: set([45])}]
    for es in edgesets:
        g = SimpleGraph(es)
        verts = set(g.vertices)
        while verts:
            assert set(es) == verts
            bcs, seps = g.biconnectedComponents()
            assert reduce(set.union, bcs) == verts
            memberbcs = dict((v, set()) for v in verts)
            for i, bc in enumerate(bcs):
                for v in bc:
                    memberbcs[v].add(i)
            parts = g.disjointPartitions()
            for v in verts:
                novparts = g.disjointPartitions(verts - set([v]))
                if g.isSeparator(v):
                    assert v in seps
                    assert len(memberbcs[v]) > 1
                    assert g.isSeparator(v)
                    assert len(novparts) == len(parts) + len(memberbcs[v]) - 1
                else:
                    assert v not in seps
                    assert len(memberbcs[v]) == 1
                    assert not g.isSeparator(v)
                    if len(g.connectedComponent(v)) == 1:
                        assert len(novparts) == len(parts) - 1
                    else:
                        assert len(novparts) == len(parts)
            for bc in bcs:
                bcs_, seps_ = g.biconnectedComponents(bc)
                assert len(bcs_) == 1
                assert bcs_[0] == bc
                assert len(seps_) == 0
                for v in bc:
                    assert bc.issubset(g.connectedComponent(v))
                    assert bc == g.connectedComponent(v, bc)
            g.removeVertex(verts.pop())


if __name__ == '__main__':
    _testGraph()
    _testGraphBiconnected()
    print "Tests passed."
    exit(0)
