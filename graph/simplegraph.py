#!/usr/bin/env python

import copy
from collections import deque
from functools import reduce


# noinspection PyPep8Naming
from graph.tree import Forest


class QueryableSimpleGraph(object):
    def __init__(self, edgeSets):
        self._edges = edgeSets
        # vertex : set of connected vertices (doubly-linked)
        # keys are vertex collection (isolated vertices have empty set)

    def assertSimple(self):
        """Test edge sets for correct simple graph properties."""
        for v, adj in self._edges.items():
            assert v not in adj
            for u in adj:
                assert u in self._edges
                assert v in self._edges[u]

    @property
    def vertices(self):
        return iter(self._edges)

    @property
    def vertexCount(self):
        return len(self._edges)

    @property
    def isolatedVertices(self):
        for v, edges in self._edges.items():
            if not edges:
                yield v

    def edgeCount(self, mask=None, *, without=None):
        """
            Return number of adjacent vertex pairs.
            mask: use only these vertices and their incident edges
            without: do not include these vertices and their edges
        """
        if mask is None and not without:
            return sum(map(len, self._edges.values())) // 2
        vertices = self._maskVertices(mask)
        if without:
            vertices = vertices - without
        halfEdges = 0
        for v in vertices:
            halfEdges += len(self._edges[v].intersection(vertices))
        return halfEdges // 2

    @property
    def edges(self):
        """Return a set of ordered 2-tuples of vertices, one per edge."""
        edgeset = set()
        for v1, adjacencies in self._edges.items():
            for v2 in adjacencies:
                edgeset.add((v1, v2) if v1 < v2 else (v2, v1))
        return edgeset

    def copyEdgeSets(self):
        return {v: adj.copy() for v, adj in self._edges.items()}

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

    def singleAdjacency(self, v):
        assert len(self._edges[v]) == 1
        return next(iter(self._edges[v]))

    def degree(self, v):
        """Return number of vertices adjacent to v."""
        return len(self._edges[v])

    def eccentricity(self, v, mask=None):
        """
            Return number of edges from v to most distant vertex.
            mask: use only these vertices and their incident edges
        """
        vertices = self._maskVertices(mask)
        visited = set()
        front = {v}
        rounds = 0
        while front:
            nextfront = reduce(set.union, (self._edges[v] for v in front))
            assert isinstance(nextfront, set)
            visited |= front
            front = (nextfront & vertices) - visited
            if front:
                rounds += 1
        return rounds

    def hyperEccentricity(self, v, mask=None):
        """
            Return sum of distances from v to all connected.
            mask: use only these vertices and their incident edges
        """
        vertices = self._maskVertices(mask)
        visited = set()
        front = {v}
        rounds = -1
        distanceSum = 0
        while front:
            rounds += 1
            distanceSum += rounds * len(front)
            nextfront = reduce(set.union, (self._edges[v] for v in front))
            assert isinstance(nextfront, set)
            visited |= front
            front = (nextfront & vertices) - visited
        return distanceSum

    def hyperDistance(self, v, targets, mask=None):
        """
            Return sum of distances from v to all reachable targets.
            mask: use only these vertices and their incident edges
        """
        vertices = self._maskVertices(mask)
        visited = set()
        front = {v}
        rounds = -1
        distanceSum = 0
        targets = set(targets)
        while front and targets:
            rounds += 1
            hits = len(front & targets)
            if hits > 0:
                distanceSum += rounds * hits
                targets -= front
            nextfront = reduce(set.union, (self._edges[v] for v in front))
            assert isinstance(nextfront, set)
            visited |= front
            front = (nextfront & vertices) - visited
        return distanceSum

    def sortClosest(self, vertices, target, mask=None):
        """
            Return 'vertices' ordered by increasing distance from 'target'.
            Unreachable vertices omitted.
            mask: use only these vertices and their incident edges
        """
        toVisit = self._maskVertices(mask)
        vertices = set(vertices)
        ordered = []
        if target in vertices:
            ordered.append(target)
            vertices.remove(target)
        bfs = deque([target])
        while vertices and bfs:
            v = bfs.popleft()
            ext = self.adjacencies(v, toVisit)
            toVisit -= ext
            for ev in ext:
                if ev in vertices:
                    ordered.append(ev)
                    vertices.remove(ev)
                bfs.append(ev)
        return ordered

    def connected(self, v1, v2, mask=None):
        """
            Return True iff there is some path from v1 to v2.
            mask: use only these vertices and their incident edges
        """
        assert v1 != v2
        if self.adjacent(v1, v2):
            return True
        toVisit = self._maskVertices(mask)
        front1, front2 = {v1}, {v2}
        while front1:
            toVisit -= front1
            front1 = reduce(set.union,
                            (self.adjacencies(v, toVisit) for v in front1))
            assert isinstance(front1, set)
            if front1.intersection(front2):
                return True
            front1, front2 = front2, front1
        return False

    def shortestPath(self, v1, v2, mask=None):
        """
            Return a minimal list of vertices connecting v1 to v2.
                path[0] == v1, path[-1] == v2
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
        leafs_a, leafs_b = {v1}, {v2}
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
            return []
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
        fronts = deque({v} for v in vertices)
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
            front = reduce(set.union,
                           (self.adjacencies(v, toVisit) for v in front))
            if not front:
                return False
            assert isinstance(front, set)
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

    def isCycle(self, p):
        """
            p is a sequence of distinct vertices.
            Return True if there are edges (p[i], p[i+1]) and (p[0], p[-1]).
        """
        assert len(p) > 1
        assert len(p) == len(set(p))
        for v1, v2 in zip(p[:-1], p[1:]):
            if v1 not in self._edges[v2]:
                return False
        return p[0] in self._edges[p[-1]]

    def biconnectedComponents(self, mask=None):
        """
            Return tuple(list(sets), set) containing the sets of vertices
            in biconnected components and the set of articulation points.
            mask: use only these vertices and their incident edges
        """
        vertices = self._maskVertices(mask)
        subtrees = dict((v, {v}) for v in vertices)
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
        return components, separators

    def connectedComponent(self, v, mask=None):
        """
            Return set of vertices connected by some path to v (including v).
            mask: use only these vertices and their incident edges
        """
        toVisit = self._maskVertices(mask)
        toVisit.add(v)
        component = {v}
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

    def isMatching(self):
        return all(len(connected) <= 1 for _, connected in self._edges.items())

    def isPerfectMatching(self):
        return self.vertexCount % 2 == 0 and\
               self.edgeCount() == self.vertexCount // 2 and\
               self.isMatching()

    def maximumMatching(self):
        """Return a graph which is a maximum matching in this."""
        matching = SimpleGraph()
        matching.addVertices(self.vertices)
        while True:
            ap = _findAugmentingPath(self, matching)
            if not ap:
                break
            # assert len(ap) % 2 == 0
            # augment matching with alternating path
            for v1, v2 in zip(ap[::2], ap[1::2]):
                matching.removeAnyEdges(v1)
                matching.removeAnyEdges(v2)
                matching.addEdge(v1, v2)
        return matching

    def _maskVertices(self, mask=None):
        """
            Return a new set containing the graph's vertices.
            mask: use only these vertices, or all vertices if None
        """
        return set(self._edges if mask is None else mask)


# noinspection PyPep8Naming
class SimpleGraph(QueryableSimpleGraph):
    def __init__(self, edgeSets=None):
        if isinstance(edgeSets, QueryableSimpleGraph):
            edgeSets = edgeSets.copyEdgeSets()
        super(SimpleGraph, self).__init__(edgeSets or {})

    def asReadOnly(self):
        """Return a read-only interface to this instance."""
        return QueryableSimpleGraph(self._edges)

    def pushVertex(self):
        """Return new vertex id."""
        v = max(self._edges) + 1 if self._edges else 0
        self.addVertex(v)
        return v

    def pushVertices(self, n):
        """Return n new vertex ids."""
        return [self.pushVertex() for _ in range(n)]

    def addVertex(self, v):
        """Add a vertex with id v."""
        if v in self._edges:
            raise ValueError
        self._edges[v] = set()

    def addVertices(self, verts):
        """Add multiple vertices with given ids."""
        for v in verts:
            self.addVertex(v)

    def removeVertex(self, v):
        """Delete a vertex and any incident edges."""
        for adj in self._edges[v]:
            self._edges[adj].remove(v)
        del self._edges[v]

    def removeVertices(self, verts):
        """Delete multiple vertices and incident edges."""
        for v in verts:
            self.removeVertex(v)

    def contractVertices(self, verts, cv=None):
        """
            verts is a collection of vertices.
            Contract all vertices in verts into a new vertex and return it.
            If cv is given, use cv for the new vertex id.
        """
        assert len(verts) > 1
        if cv is None:
            cv = self.pushVertex()
        else:
            self.addVertex(cv)
        connected = set()
        for v in verts:
            connected |= self._edges[v]
            self.removeVertex(v)
        connected -= set(verts)
        for v in connected:
            self.addEdge(cv, v)
        return cv

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

    def removeAnyEdges(self, v):
        """Delete any/all edges incident to v."""
        for adj in self._edges[v]:
            self._edges[adj].remove(v)
        self._edges[v].clear()


def _findAugmentingPath(G, M):
    unmarkedVerts = set(G.vertices)
    unmarkedEdges = G.edges - M.edges
    forest = Forest()
    for v in M.isolatedVertices:
        forest.addTree(v)
    while True:
        v = None
        for _v in unmarkedVerts:
            if _v in forest and forest.depthOf(_v) % 2 == 0:
                v = _v
                break
        if v is None:
            break

        while True:
            e = None
            for _e in unmarkedEdges:
                if v in _e:
                    e = _e
                    break
            if e is None:
                break

            w = e[1] if e[0] == v else e[0]
            if w not in forest:
                x = M.singleAdjacency(w)
                forest.add(w, v)
                forest.add(x, w)
            else:
                if forest.depthOf(w) % 2 == 0:
                    if forest.rootFor(v) != forest.rootFor(w):
                        p = forest.pathToRoot(v)
                        p.reverse()
                        p.extend(forest.pathToRoot(w))
                        # assert len(p) % 2 == 0
                        return p
                    else:
                        B = forest.findPath(v, w)
                        # assert len(B) % 2 == 1
                        # assert G.isCycle(B)
                        Gc = copy.deepcopy(G)
                        vb = Gc.contractVertices(B)
                        Mc = copy.deepcopy(M)
                        Mc.contractVertices(B, vb)
                        p = _findAugmentingPath(Gc, Mc)
                        if vb in p:
                            p_in = p[:p.index(vb)]
                            p_out = p[p.index(vb) + 1:]
                            if not p_out:
                                # p[-1] was vb, make like p[0] was vb
                                p_out = p_in
                                p_out.reverse()
                                p_in = []
                            if p_in:
                                for i, B_v in enumerate(B):
                                    if G.adjacent(B_v, p_in[-1]):
                                        B = B[i:] + B[:i]
                                        break
                            B_r = B[:1] + list(reversed(B[1:]))
                            while len(B) > 2 and not G.adjacent(p_out[0], B[-1]):
                                B = B[:-2]
                            while len(B_r) > 2 and not G.adjacent(p_out[0], B_r[-1]):
                                B_r = B_r[:-2]
                            if len(B_r) > len(B):
                                B = B_r
                            p = p_in + B + p_out
                        # assert len(p) % 2 == 0
                        return p
            unmarkedEdges.remove(e)
        unmarkedVerts.remove(v)
    return []
