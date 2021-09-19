#!/usr/bin/env python

from collections import deque
from itertools import count
from functools import reduce


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

    def copyEdgeSets(self):
        return dict((v, adj.copy()) for v, adj in self._edges.items())

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

    def paths(self):
        innervs = set(v for v, e in self._edges.items() if len(e) == 2)
        paths = []
        while innervs:
            v = innervs.pop()
            p = list(self._edges[v])
            p.insert(1, v)
            while p[-1] in innervs:
                innervs.remove(p[-1])
                ext = (self._edges[p[-1]] - set(p[-2:])).pop()
                if ext != p[1]:
                    p.append(ext)
            while p[0] in innervs:
                innervs.remove(p[0])
                ext = (self._edges[p[0]] - set(p[:2])).pop()
                if ext != p[-2]:
                    p.insert(0, ext)
            paths.append(p)
        return paths

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
        front1, front2 = set([v1]), set([v2])
        while front1:
            toVisit -= front1
            front1 = reduce(set.union,
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
            front = reduce(set.union,
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
        if isinstance(edgeSets, QueryableSimpleGraph):
            edgeSets = edgeSets.copyEdgeSets()
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
            (self._keys,
             self._vertices,
             self._components,
             self._biconComponents,
             self._separators,
             self._biconComponentMap,
             self._separatorMap) = state
        self._c_k_deleted = None
        self._c_k_reduced = None
        self._c_kset_new = None
        self._separatorsChanged = False

    def copy(self):
        return OnlineReducedGraph(self._graph, (
            self._keys,
            self._vertices,
            self._components,
            self._biconComponents,
            self._separators,
            self._biconComponentMap,
            self._separatorMap))

    @property
    def componentDeleted(self):
        return self._c_k_deleted

    @property
    def componentReduced(self):
        return self._c_k_reduced

    @property
    def newSubComponents(self):
        return self._c_kset_new

    @property
    def separatorsChanged(self):
        return self._separatorsChanged

    @property
    def allMasked(self):
        return not self._vertices

    @property
    def disjoint(self):
        return len(self._components) > 1

    @property
    def vertices(self):
        return self._vertices

    @property
    def components(self):
        return self._components

    def blockForest(self):
        bf = SimpleGraph()
        vertexmap = {}  # vertex: vertex in block forest
        articulations = set()  # separators mapped to block forest
        for sv in self._separators:
            av = bf.pushVertex()
            articulations.add(av)
            vertexmap[sv] = av
        for bc_k, bc in self._biconComponents.items():
            seps = self._separatorMap[bc_k]
            if len(bc) == 2 and len(seps) == 2:
                it = iter(bc)
                bf.addEdge(vertexmap[next(it)], vertexmap[next(it)])
            else:
                bcv = bf.pushVertex()
                for v in bc - seps:
                    vertexmap[v] = bcv
                for sv in seps:
                    bf.addEdge(bcv, vertexmap[sv])
        return (bf, vertexmap, articulations)

    def maskVertex(self, v):
        self._vertices = self._vertices.copy()
        self._vertices.remove(v)
        # self._vertices valid

        self._components = self._components.copy()
        c_k = self._findComponent(v)
        self._c_k_deleted = None
        self._c_k_reduced = None
        self._c_kset_new = None
        c = self._components[c_k]
        if len(c) == 1:
            self._c_k_deleted = c_k
            del self._components[c_k]
        else:
            c = c.copy()
            c.remove(v)
            if v in self._separators:
                self._c_k_deleted = c_k
                del self._components[c_k]
                self._c_kset_new = set()
                for c_new in self._graph.disjointPartitions(c):
                    c_k_new = next(self._keys)
                    self._components[c_k_new] = c_new
                    self._c_kset_new.add(c_k_new)
                #assert len(self._c_kset_new) > 1
            else:
                self._c_k_reduced = c_k
                self._components[c_k] = c
        # self._components valid

        self._biconComponents = self._biconComponents.copy()
        self._separatorMap = self._separatorMap.copy()
        self._biconComponentMap = self._biconComponentMap.copy()
        bc_kset = self._biconComponentMap.pop(v).copy()
        bc_kset_reduced = None
        if self._c_k_deleted:
            if self._c_kset_new:
                #assert len(bc_kset) > 1
                bc_kset_reduced = bc_kset
            else:
                #assert len(bc_kset) == 1
                #assert len(self._biconComponents[bc_k]) == 1
                #assert v not in self._separators
                #assert len(self._separatorMap[bc_k]) == 0
                bc_k = bc_kset.pop()
                del self._biconComponents[bc_k]
                del self._separatorMap[bc_k]
        else:
            #assert self._c_k_reduced
            #assert v not in self._separators
            #assert len(bc_kset) == 1
            bc_kset_reduced = bc_kset

        if bc_kset_reduced:
            separators = self._separators.copy()
            separators.discard(v)
            while bc_kset_reduced:
                bc_k = bc_kset_reduced.pop()
                bc_reduced = self._biconComponents[bc_k].copy()
                bc_reduced.remove(v)

                if len(bc_reduced) == 1:
                    other = next(iter(bc_reduced))
                    bc_kset_other = self._biconComponentMap[other]
                    if len(bc_kset_other) > 1:
                        # what's left of bc_reduced is a subset of
                        # another biconnected component
                        bc_kset_other = bc_kset_other.copy()
                        bc_kset_other.remove(bc_k)
                        self._biconComponentMap[other] = bc_kset_other
                        del self._biconComponents[bc_k]
                        del self._separatorMap[bc_k]
                        if len(bc_kset_other) == 1:
                            separators.remove(other)
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
                    for newbc_k, newbc in zip(self._keys, bcs):
                        self._biconComponents[newbc_k] = newbc
                        self._separatorMap[newbc_k] = newbc & (oldseps | seps)
                        for bcv in newbc:
                            self._biconComponentMap[bcv].add(newbc_k)
                    separators |= seps
                else:
                    self._biconComponents[bc_k] = bc_reduced
                    seps = self._separatorMap[bc_k]
                    if v in seps:
                        seps = seps.copy()
                        seps.remove(v)
                        self._separatorMap[bc_k] = seps

            if separators != self._separators:
                self._separators = separators
                self._separatorsChanged = True

    def adjacencies(self, v):
        return self._graph.adjacencies(v, self._vertices)

    def componentAdjacencies(self, v, k):
        return self._graph.adjacencies(v, self._components[k])

    def componentsAdjacencies(self, v, kset):
        mask = reduce(set.union, map(self._components.get, kset))
        return self._graph.adjacencies(v, mask)

    def sortClosest(self, vertices, target):
        return self._graph.sortClosest(vertices, target, self._vertices)

    def isSeparator(self, v):
        return v in self._separators

    def biconnectedComponents(self):
        return (self._biconComponents.values(), self._separators)

    def connectedComponent(self, v):
        return self._components[self._findComponent(v)]

    def disjointPartitions(self):
        return self._components.values()

    def adjacentComponents(self, v):
        adj = self._graph.adjacencies(v, self._vertices)
        return set(c_k for c_k, c in self._components.items() if adj & c)

    def _findComponent(self, v):
        for c_k, c in self._components.items():
            if v in c:
                return c_k
        raise KeyError()

    def _initializeState(self):
        # self._vertices           set of unmasked vertices
        # self._components         key: set of vertices
        # self._biconComponents    key: set of vertices
        # self._separators         set of vertices
        # self._biconComponentMap  v: set of bicon component keys
        # self._separatorMap       bicon component key: set of separators

        self._keys = count(1)

        self._vertices = set(self._graph.vertices)
        self._components = \
            dict(zip(self._keys, self._graph.disjointPartitions()))

        bcs, seps = self._graph.biconnectedComponents()
        self._biconComponents = dict(zip(self._keys, bcs))
        self._separators = seps

        self._biconComponentMap = dict((v, set()) for v in self._vertices)
        self._separatorMap = dict((k, set()) for k in self._biconComponents)
        for k, bc in self._biconComponents.items():
            for v in bc:
                self._biconComponentMap[v].add(k)
                if v in self._separators:
                    self._separatorMap[k].add(v)
