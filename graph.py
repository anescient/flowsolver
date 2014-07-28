#!/usr/bin/env python


class SimpleGraph(object):
    def __init__(self):
        self._nextVertex = 0  # incrementing index
        self._edges = {}  # vertex : set of connected vertices (doubly-linked)
                          # keys are vertex collection (may have empty values)

    @property
    def vertices(self):
        return self._edges.keys()

    def pushVertex(self):
        """Return new vertex id."""
        v = self._nextVertex
        self._nextVertex += 1
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
        assert v1 not in self._edges[v2]
        assert v2 not in self._edges[v1]
        self._edges[v1].add(v2)
        self._edges[v2].add(v1)

    def adjacent(self, v1, v2):
        """Return True iff v1 and v2 share an edge."""
        return v2 in self._edges[v1]

    def adjacencies(self, v):
        """Return set of vertices adjacent to v. Never includes v."""
        return self._edges[v]

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
            toVisit |= self.adjacencies(v).intersection(openVerts)
        return component

    def connectedComponentMasked(self, v, maskVertices=None):
        """
            maskVertices: exclude these vertices and their incident edges
            Return set of vertices connected by some path to v (including v).
        """
        if maskVertices is None:
            return self.connectedComponent(v)
        else:
            return self.connectedComponent(v, \
                set(self.vertices) - set(maskVertices))

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

    def disjointPartitionsMasked(self, maskVertices=None):
        """
            maskVertices: exclude these vertices and their incident edges
            Return list of sets of vertices.
            Vertices in each set are connected.
            Sets are not connected to each other.
        """
        if maskVertices is None:
            return self.disjointPartitions()
        else:
            return self.disjointPartitions(\
                set(self.vertices) - set(maskVertices))


def _test():
    g = SimpleGraph()
    verts = []
    for i in xrange(10):
        verts.append(g.pushVertex())
    assert len(set(verts)) == len(verts)
    for v in verts:
        assert len(g.adjacencies(v)) == 0
        assert g.connectedComponentMasked(v) == set([v])
    parts = g.disjointPartitionsMasked()
    assert len(parts) == len(verts)
    s = set()
    for p in parts:
        assert len(p) == 1
        s.add(p.pop())
    assert s == set(verts)
    for i in xrange(len(verts) - 1):
        g.addEdge(verts[i], verts[i + 1])
    for v in verts:
        assert g.connectedComponentMasked(v) == set(verts)
    parts = g.disjointPartitionsMasked(verts[2:3])
    assert len(parts) == 2
    assert len(parts[0].intersection(parts[1])) == 0
    assert verts[2] not in parts[0].union(parts[1])
    assert parts[0].union(parts[1]) == set(verts) - set(verts[2:3])
    drops = [verts[i] for i in [2, 5, 8]]
    for v in drops:
        g.removeVertex(v)
        verts.remove(v)
    assert len(g.adjacencies(verts[-1])) == 0
    for v in verts[:-1]:
        assert len(g.adjacencies(v)) == 1
    assert len(g.disjointPartitionsMasked()) == 4
    assert len(g.disjointPartitionsMasked(verts[:1])) == 4
    assert len(g.disjointPartitionsMasked(verts[:2])) == 3
    assert g.connectedComponentMasked(verts[-1]) == set(verts[-1:])
    assert g.connectedComponentMasked(verts[1], verts[:1]) == set(verts[1:2])
    backbone = [list(p)[0] for p in g.disjointPartitionsMasked()]
    for i in xrange(len(backbone) - 1):
        g.addEdge(backbone[i], backbone[i + 1])
    g.addEdge(backbone[0], backbone[-1])
    assert len(g.disjointPartitionsMasked()) == 1
    assert g.connectedComponentMasked(verts[0]) == set(verts)
    print "Tests passed."
    return 0

if __name__ == '__main__':
    exit(_test())
