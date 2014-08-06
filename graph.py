#!/usr/bin/env python


class QueryableSimpleGraph(object):
    def __init__(self, edgeSets):
        self._edges = edgeSets
        # vertex : set of connected vertices (doubly-linked)
        # keys are vertex collection (may have empty values)

        for v, adj in edgeSets.iteritems():
            assert v not in adj
            for u in adj:
                assert u in edgeSets
                assert v in edgeSets[u]

    @property
    def vertices(self):
        return iter(self._edges)

    def copyEdgeSets(self):
        edgesets = self._edges.copy()
        for v in edgesets:
            edgesets[v] = edgesets[v].copy()
        return edgesets

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

    def separators(self, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Return vertices which divide their connected component.
        """
        vertices = set(self.vertices if vertices is None else vertices)
        if not vertices:
            return []
        toVisit = vertices.copy()
        tree = Tree(toVisit.pop())
        stack = [tree.root]
        lowpoint = {}
        separators = set()
        rootchildren = 0
        while stack:
            v = stack[-1]
            pushv = next(iter(self.adjacencies(v, toVisit)), None)
            if pushv is None:
                stack.pop()
                if not stack:
                    break  # following test doesn't work for root
                lowpoint[v] = tree.depthOf(v)
                for nv in self.adjacencies(v, vertices):
                    if nv != tree.parent(v):
                        lowpoint[v] = min(lowpoint[v], tree.depthOf(nv))
                for cv in tree.children(v):
                    lowpoint[v] = min(lowpoint[v], lowpoint[cv])
                    if lowpoint[cv] >= tree.depthOf(v):
                        separators.add(v)
            else:
                if len(stack) == 1:
                    rootchildren += 1
                toVisit.remove(pushv)
                tree.add(pushv, v)
                stack.append(pushv)
        if rootchildren > 1:
            separators.add(tree.root)
        trees = [tree]
        if toVisit:
            t, s = self.separators(toVisit)
            trees.extend(t)
            separators |= s
        return (trees, separators)

    def depthFirstTree(self, root, vertices=None):
        """
            vertices: use only these vertices and their incident edges
                      if None, use all vertices in graph
            Start at root, making it the root of the tree.
            Return instance of Tree including vertices connected to root.
        """
        openVerts = set(self.vertices if vertices is None else vertices)
        assert root in openVerts
        openVerts.remove(root)
        tree = Tree(root)
        stack = [root]
        while stack:
            v = stack[-1]
            cv = next(iter(self.adjacencies(v, openVerts)), None)
            if cv is None:
                stack.pop()
            else:
                openVerts.remove(cv)
                tree.add(cv, v)
                stack.append(cv)
                assert tree.depthOf(cv) == len(stack) - 1
        return tree

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
        super(SimpleGraph, self).__init__({})

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


class Tree(object):
    def __init__(self, root):
        self._root = root
        self._nodes = {}  # vertex : (parent, depth)
        self._nodes[root] = (None, 0)

    @property
    def root(self):
        return self._root

    @property
    def edges(self):
        for v, (pv, _) in self._nodes.iteritems():
            if pv is not None:
                yield (pv, v)

    def __contains__(self, v):
        return v in self._nodes

    def add(self, v, parent):
        assert v not in self._nodes
        self._nodes[v] = (parent, self.depthOf(parent) + 1)

    def depthOf(self, v):
        return self._nodes[v][1]

    def parent(self, v):
        return self._nodes[v][0]

    def children(self, v):
        return (cv for cv, (pv, _) in self._nodes.iteritems() if pv == v)

    def findPath(self, v, u):
        assert v in self._nodes
        assert u in self._nodes
        v_path = [v]  # path from v toward root
        u_path = [u]  # path from u toward root
        while v_path[-1] != u_path[-1]:
            advance_v = self.depthOf(v_path[-1]) > self.depthOf(u_path[-1])
            advance_u = self.depthOf(u_path[-1]) > self.depthOf(v_path[-1])
            if advance_v or not advance_u:
                v_path.append(self._nodes[v_path[-1]][0])
            if advance_u or not advance_v:
                u_path.append(self._nodes[u_path[-1]][0])
        v_path.extend(reversed(u_path[:-1]))
        return v_path

    def pathToRoot(self, v):
        v_path = [v]
        while v_path[-1] != self._root:
            v_path.append(self.parent(v_path[-1]))
        return v_path


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


def _testTree():
    t = Tree(1)
    assert t.root == 1
    assert 1 in t
    assert t.depthOf(1) == 0
    assert t.parent(1) is None
    assert t.findPath(1, 1) == [1]
    t.add(2, 1)
    assert t.depthOf(2) == 1
    assert t.parent(2) == 1
    t.add(3, 1)
    assert t.findPath(2, 3) == [2, 1, 3]
    t.add(4, 2)
    t.add(5, 3)
    assert t.findPath(4, 5) == [4, 2, 1, 3, 5]
    assert t.findPath(2, 5) == [2, 1, 3, 5]
    assert t.findPath(4, 3) == [4, 2, 1, 3]
    t.add(6, 2)
    t.add(7, 2)
    t.add(9, 7)
    assert t.findPath(6, 3) == [6, 2, 1, 3]
    assert t.findPath(6, 9) == [6, 2, 7, 9]


if __name__ == '__main__':
    _testGraph()
    _testTree()
    print "Tests passed."
    exit(0)
