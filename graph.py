#!/usr/bin/env python


class QueryableSimpleGraph(object):
    def __init__(self, edgeSets=None):
        self._edges = {}  # vertex : set of connected vertices (doubly-linked)
                          # keys are vertex collection (may have empty values)
        if edgeSets:
            for v, adj in edgeSets.iteritems():
                assert v not in adj
                for u in adj:
                    assert u in edgeSets
                    assert v in edgeSets[u]
            self._edges = edgeSets

    @property
    def vertices(self):
        return iter(self._edges)

    def adjacent(self, v1, v2):
        """Return True iff v1 and v2 share an edge."""
        return v2 in self._edges[v1]

    def adjacencies(self, v, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return set of vertices adjacent to v. Never includes v.
        """
        if vertices is None:
            return self._edges[v].copy()
        else:
            return self._edges[v].intersection(vertices)

    def connected(self, v1, v2, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return True iff there is some path from v1 to v2.
        """
        assert v1 != v2
        if v2 in self._edges[v1]:
            return True
        openVerts = set(self.vertices if vertices is None else vertices)
        openVerts.discard(v1)
        openVerts.discard(v2)
        front1 = self.adjacencies(v1, openVerts)
        front2 = self.adjacencies(v2, openVerts)
        if not front1 or not front2:
            return False
        flip = False
        while not front1.intersection(front2):
            if flip:
                openVerts -= front1
                front1 = set.union(\
                    *(self.adjacencies(fv, openVerts) for fv in front1))
                if not front1:
                    return False
            else:
                openVerts -= front2
                front2 = set.union(\
                    *(self.adjacencies(fv, openVerts) for fv in front2))
                if not front2:
                    return False
            flip = not flip
        return True

    def isConnectedSet(self, vset, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return True iff all vertices in vset are connected.
        """
        if len(vset) == 1:
            return True
        elif len(vset) == 2:
            it = iter(vset)
            return self.connected(next(it), next(it), vertices)
        openVerts = set(self.vertices if vertices is None else vertices)
        openVerts |= vset
        fronts = [self.adjacencies(v, openVerts) for v in vset]
        if not all(fronts):
            return False
        openVerts -= vset
        while len(fronts) > 1:
            front = fronts.pop(0)
            joined = False
            for joinfront in fronts:
                if front.intersection(joinfront):
                    joinfront |= front
                    joined = True
            if joined:
                continue
            openVerts -= front
            front = set.union(\
                *(self.adjacencies(fv, openVerts) for fv in front))
            if not front:
                return False
            fronts.append(front)
        return True

    def isSeparator(self, v, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return True iff removing v will divide v's connected component.
        """
        openVerts = set(self.vertices if vertices is None else vertices)
        links = self.adjacencies(v, openVerts)
        if len(links) < 2:
            return False
        openVerts.discard(v)
        return not self.isConnectedSet(links, openVerts)

    def isBiconnected(self, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return True iff graph is connected and no vertex is a separator.
        """
        pass

    def biconnectedComponents(self, vertices=None):
        pass

    def connectedComponent(self, v, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return set of vertices connected by some path to v (including v).
        """
        openVerts = set(self.vertices if vertices is None else vertices)
        openVerts.add(v)
        component = set()
        toVisit = set([v])
        while toVisit:
            v = toVisit.pop()
            component.add(v)
            openVerts.remove(v)
            toVisit |= self.adjacencies(v, openVerts)
        return component

    def disjointPartitions(self, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return list of sets of vertices.
            Vertices in each set are connected.
            Sets are not connected to each other.
        """
        toVisit = set(self.vertices if vertices is None else vertices)
        partitions = []
        while toVisit:
            p = self.connectedComponent(toVisit.pop(), toVisit)
            toVisit -= p
            partitions.append(p)
        return partitions


class SimpleGraph(QueryableSimpleGraph):
    def __init__(self):
        super(SimpleGraph, self).__init__()

    def asReadOnly(self):
        return QueryableSimpleGraph(self._edges)

    def pushVertex(self):
        """Return new vertex id."""
        v = max(self._edges) + 1 if self._edges else 0
        self._edges[v] = set()
        return v

    def removeVertex(self, v):
        """Delete a vertex and any related edges."""
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
        """Disconnect v1 and v2. Error if not connected."""
        assert v1 != v2
        self._edges[v1].remove(v2)
        self._edges[v2].remove(v1)


def _test():
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


if __name__ == '__main__':
    _test()
    print "Tests passed."
    exit(0)
