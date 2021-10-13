#!/usr/bin/env python

from functools import reduce
from itertools import count, combinations

from graph import SimpleGraph


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
        """Key of component eliminated in last op, or None"""
        return self._c_k_deleted

    @property
    def componentReduced(self):
        """Key of component reduced in last op, or None"""
        return self._c_k_reduced

    @property
    def newSubComponents(self):
        """Keys of (sub)components created in last op, or None"""
        return self._c_kset_new

    @property
    def separatorsChanged(self):
        """Whether or not separators were changed in last op"""
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

    def edgeCount(self):
        return self._graph.edgeCount(self._vertices)

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
        return bf, vertexmap, articulations

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
                # assert len(self._c_kset_new) > 1
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
                # assert len(bc_kset) > 1
                bc_kset_reduced = bc_kset
            else:
                # assert len(bc_kset) == 1
                # assert len(self._biconComponents[bc_k]) == 1
                # assert v not in self._separators
                # assert len(self._separatorMap[bc_k]) == 0
                bc_k = bc_kset.pop()
                del self._biconComponents[bc_k]
                del self._separatorMap[bc_k]
        else:
            # assert self._c_k_reduced
            # assert v not in self._separators
            # assert len(bc_kset) == 1
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
        """Get neighbors of v"""
        return self._graph.adjacencies(v, self._vertices)

    def componentAdjacencies(self, v, k):
        """Get neighbors of v in component k"""
        return self._graph.adjacencies(v, self._components[k])

    def componentsAdjacencies(self, v, kset):
        """Get neighbors of v in any of many components"""
        mask = reduce(set.union, map(self._components.get, kset))
        return self._graph.adjacencies(v, mask)

    def eccentricity(self, v, omit=None):
        verts = self._vertices
        if omit:
            verts = self._vertices - omit
        return self._graph.eccentricity(v, verts)

    def hyperEccentricity(self, v, omit=None):
        verts = self._vertices
        if omit:
            verts = self._vertices - omit
        return self._graph.hyperEccentricity(v, verts)

    def hyperDistance(self, v, targets):
        return self._graph.hyperDistance(v, targets, self._vertices)

    def sortClosest(self, vertices, target):
        return self._graph.sortClosest(vertices, target, self._vertices)

    def isSeparator(self, v):
        return v in self._separators

    def biconnectedComponents(self):
        return self._biconComponents.values(), self._separators

    def connectedComponent(self, v):
        return self._components[self._findComponent(v)]

    def disjointPartitions(self):
        return self._components.values()

    def adjacentComponents(self, v):
        adj = self._graph.adjacencies(v, self._vertices)
        return set(c_k for c_k, c in self._components.items() if adj & c)

    def shortestPath(self, v1, v2):
        return self._graph.shortestPath(v1, v2, self._vertices)

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

    def _assertValidState(self):
        assert self._vertices == set(self._biconComponentMap)
        componentSum = set()
        for k, c in self._components.items():
            assert c
            assert not c & componentSum
            componentSum |= c
        assert self._vertices == componentSum
        for v, kset in self._biconComponentMap.items():
            assert kset
            assert (len(kset) > 1) == (v in self._separators)
            for k in kset:
                assert v in self._biconComponents[k]
        assert set(self._separatorMap) == set(self._biconComponents)
        for k, vset in self._separatorMap.items():
            assert vset == self._separators & self._biconComponents[k]
        for bc1, bc2 in combinations(self._biconComponents.values(), 2):
            assert len(bc1 & bc2) < 2
            assert not bc1.issubset(bc2)
            assert not bc2.issubset(bc1)
        bcs, seps = self._graph.biconnectedComponents(self._vertices)
        assert seps == self._separators
        assert len(bcs) == len(self._biconComponents)
        for k, bc in self._biconComponents.items():
            assert bc
            bcs, seps = self._graph.biconnectedComponents(bc)
            assert len(bcs) == 1 and not seps
            for v, kset in self._biconComponentMap.items():
                assert (k in kset) == (v in bc)
