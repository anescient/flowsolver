#!/usr/bin/env python

from itertools import islice, chain, izip
from gridgraph import GraphOntoRectangularGrid


class FlowBoardSolver(object):
    def __init__(self, board):
        self._gridgraph = GraphOntoRectangularGrid(board.size)
        for xy in board.bridges:
            self._gridgraph.addBridge(xy)
        self._endpoints = []
        for k, xy1, xy2 in board.endpointPairs:
            self._endpoints.append((k,
                                    self._gridgraph.singleVertexAt(xy1), \
                                    self._gridgraph.singleVertexAt(xy2)))
        self._solver = FlowGraphSolver(self._gridgraph.getGraphCopy(), \
            [(v1, v2) for _, v1, v2 in self._endpoints])

    @property
    def done(self):
        return self._solver.done

    def run(self, limit=None):
        return self._solver.run(limit)

    def printStats(self):
        self._solver.printStats()

    def getFlows(self):
        for vflow in self._solver.getFlows():
            yield (self._keyAt(vflow[0]), \
                   list(map(self._gridgraph.locationForVertex, vflow)))

    def _keyAt(self, v):
        for k, v1, v2 in self._endpoints:
            if v1 == v or v2 == v:
                return k
        return None


class FlowGraphSolver(object):

    class Frame(object):

        def __init__(self, graph, headpairs, \
                     openverts, components, commoncomponents):
            self._graph = graph
            self._headpairs = headpairs
            self._openverts = openverts
            self._components = components
            self._commoncomponents = commoncomponents
            self._framegen = None
            self._framestaken = 0
            self._coverstate = None
            self._moveapplied = None

        @property
        def moveApplied(self):
            return self._moveapplied

        @property
        def headPairs(self):
            return iter(self._headpairs)

        @property
        def framesTaken(self):
            return self._framestaken

        @property
        def coverState(self):
            """
                Return a hashable value unique to the set of open vertices and
                the locations of unconnected path heads.
            """
            if self._coverstate is None:
                self._coverstate = (frozenset(self._headpairs),
                                    frozenset(self._openverts))
            return self._coverstate

        def isSolved(self):
            return not self._openverts and not self._headpairs

        def copy(self, move=None):
            frame = self.__class__(\
                self._graph, self._headpairs, \
                self._openverts, self._components, self._commoncomponents)
            if move:
                frame.applyMove(*move)
            return frame

        def applyMove(self, vidx, to):
            assert self._moveapplied is None
            pairidx = vidx // 2
            subidx = vidx % 2
            oldpair = self._headpairs[pairidx]
            head, other = oldpair[subidx], oldpair[1 - subidx]
            self._moveapplied = (head, to)
            self._headpairs = list(self._headpairs)
            self._commoncomponents = list(self._commoncomponents)
            if to == other:
                self._headpairs.pop(pairidx)
                self._commoncomponents.pop(pairidx)
            else:
                self._headpairs[pairidx] = \
                    (to, other) if to < other else (other, to)
                self._closeVertex(to)

                toadj = self._graph.adjacencies(to)
                common = None
                for k in self._commoncomponents[pairidx]:
                    if not toadj & self._components[k]:
                        if common is None:
                            common = self._commoncomponents[pairidx].copy()
                        common.remove(k)
                if common is not None:
                    self._commoncomponents[pairidx] = common

        def _closeVertex(self, v):
            self._openverts = self._openverts.copy()
            self._openverts.remove(v)
            self._components = self._components.copy()
            k_deleted = None
            k_reduced = None
            subcomps = None
            for k, c in self._components.iteritems():
                if v in c:
                    c = c.copy()
                    c.remove(v)
                    if c:
                        if self._graph.isSeparator(v, c):
                            newk = max(self._components) + 1
                            del self._components[k]
                            k_deleted = k
                            subcomps = {}
                            for newc in self._graph.disjointPartitions(c):
                                subcomps[newk] = newc
                                newk += 1
                        else:
                            self._components[k] = c
                            k_reduced = k
                    else:
                        del self._components[k]
                        k_deleted = k
                    break

            if k_reduced is not None:
                assert k_deleted is None and subcomps is None
                reduced = self._components[k_reduced]
                for i, (v1, v2) in enumerate(self._headpairs):
                    common = self._commoncomponents[i]
                    if k_reduced in common:
                        adj1 = self._graph.adjacencies(v1)
                        adj2 = self._graph.adjacencies(v2)
                        if (v in adj1 and not adj1 & reduced) or \
                           (v in adj2 and not adj2 & reduced):
                            common = common.copy()
                            common.remove(k_reduced)
                            self._commoncomponents[i] = common
            else:
                assert k_deleted is not None
                for i, (v1, v2) in enumerate(self._headpairs):
                    common = self._commoncomponents[i]
                    if k_deleted in common:
                        common = common.copy()
                        common.remove(k_deleted)
                        if subcomps:
                            adj1 = self._graph.adjacencies(v1)
                            adj2 = self._graph.adjacencies(v2)
                            for k, c in subcomps.iteritems():
                                if adj1 & c and adj2 & c:
                                    common.add(k)
                        self._commoncomponents[i] = common

            if subcomps:
                self._components.update(subcomps)

        def heuristicUnsolvable(self):
            # check that all pairs can be connected and
            # all open vertices can be reached by some pair
            covered = set()
            for common, (v1, v2) in izip(self._commoncomponents, \
                                         self._headpairs):
                if not common and not self._graph.adjacent(v1, v2):
                    return True
                covered |= common
            if len(covered) != len(self._components):
                return True

            # check if any open vertex is adjacent only to
            # one other open vertex or one path head
            if self._moveapplied:  # assume parent frames have been checked
                checkverts = self._graph.adjacencies(self._moveapplied[0]) | \
                             self._graph.adjacencies(self._moveapplied[1])
                checkverts &= self._openverts
            else:
                checkverts = self._openverts
            active = self._openverts.union(chain(*self._headpairs))
            for v in checkverts:
                x = len(self._graph.adjacencies(v, active))
                assert x > 0
                if x == 1:
                    return True
            return False

        def takeNextFrame(self):
            if self._framegen is None:
                self._framegen = self._nextFrames()
            frame = next(self._framegen, None)
            if frame:
                self._framestaken += 1
            return frame

        def _nextFrames(self):
            movesets = self._possibleMoves()
            best = None
            for vidx, moves in movesets.iteritems():
                if best is None or len(moves) < len(best[1]):
                    best = (vidx, moves)
                if len(moves) == 1:
                    break

            if len(best[1]) > 1:
                leafmoves = self._leafMoves(movesets)
                if leafmoves:
                    return (self.copy(move) for move in leafmoves)
            return (self.copy((best[0], to)) for to in best[1])

        def _possibleMoves(self):
            moves = {}  # vidx : set of vertices to move to
            for pairidx, (v1, v2) in enumerate(self._headpairs):
                common = self._commoncomponents[pairidx]
                if len(common) == 1:
                    openverts = self._components[next(iter(common))]
                else:
                    openverts = set()
                    for c in map(self._components.get, common):
                        openverts |= c
                m1 = self._graph.adjacencies(v1, openverts)
                m2 = self._graph.adjacencies(v2, openverts)
                if self._graph.adjacent(v1, v2):
                    m1.add(v2)
                    m2.add(v1)
                assert m1 and m2
                moves[2 * pairidx] = m1
                moves[2 * pairidx + 1] = m2
            return moves

        def _leafMoves(self, movesets):
            """return list of (vidx, move) or None"""
            # if any open vertex has 0 or 1 adjacent open vertices,
            # it must be connected now via some adjacent path head
            allmoves = reduce(set.union, movesets.values(), set())
            leaf = None
            for m in allmoves.intersection(self._openverts):
                if len(self._graph.adjacencies(m, self._openverts)) < 2:
                    leaf = m
                    break
            if leaf is None:
                return None
            leafmoves = []
            for vidx, moves in movesets.iteritems():
                if leaf in moves:
                    leafmoves.append((vidx, leaf))
            return leafmoves

        @classmethod
        def initial(cls, graph, endpointpairs):
            assert all(len(vp) == 2 for vp in endpointpairs)
            assert len(reduce(set.union, map(set, endpointpairs), set())) == \
                   2 * len(endpointpairs)
            headpairs = [tuple(sorted(ep)) for ep in endpointpairs]
            openverts = set(graph.vertices)
            openverts -= set(v for vp in endpointpairs for v in vp)
            components = dict(enumerate(graph.disjointPartitions(openverts)))
            commoncomponents = []
            for v1, v2 in headpairs:
                adj1 = graph.adjacencies(v1, openverts)
                adj2 = graph.adjacencies(v2, openverts)
                common = set()
                for k, c in components.iteritems():
                    if adj1 & c and adj2 & c:
                        common.add(k)
                commoncomponents.append(common)
            return cls(graph, headpairs, \
                       openverts, components, commoncomponents)

        @staticmethod
        def recoverPaths(framestack):
            if not framestack:
                return []
            pathpairs = [([v1], [v2]) for v1, v2 in framestack[0].headPairs]
            for frame in framestack[1:]:
                for path in (p for pp in pathpairs for p in pp):
                    if path[-1] == frame.moveApplied[0]:
                        path.append(frame.moveApplied[1])
            paths = []
            for p1, p2 in pathpairs:
                if p1[-1] == p2[-1]:
                    paths.append(p1[:-1] + list(reversed(p2)))
                else:
                    paths.append(p1)
                    paths.append(p2)
            return paths

    class Memo(object):
        def __init__(self):
            self._memo = {}
            self._inserts = 0
            self._finds = 0
            self._hits = 0
            self._limit = 20000

        @property
        def inserts(self):
            return self._inserts

        @property
        def hitRate(self):
            return 0 if self._hits == 0 else self._hits / float(self._finds)

        @property
        def returnRate(self):
            return 0 if self._hits == 0 else self._hits / float(self._inserts)

        def insert(self, frame):
            self._inserts += 1
            if len(self._memo) >= self._limit:
                self._prune(3 * self._limit // 4)
            self._memo[frame.coverState] = self._finds

        def find(self, frame):
            self._finds += 1
            hit = frame.coverState in self._memo
            if hit:
                self._hits += 1
                self._memo[frame.coverState] = self._finds
            return hit

        def _prune(self, limit):
            keep = islice(\
                sorted(self._memo, key=self._memo.get, reverse=True), limit)
            self._memo = dict((k, self._memo[k]) for k in keep)

    def __init__(self, graph, endpointpairs):
        self._stack = [self.Frame.initial(graph, endpointpairs)]
        self._totalframes = 1
        self._memo = self.Memo()

    @property
    def done(self):
        return not self._stack or self._stack[-1].isSolved()

    def run(self, limit=None):
        if self.done:
            return True
        newtop = False
        while self._stack:
            nextframe = self._stack[-1].takeNextFrame()
            if nextframe:
                self._totalframes += 1
                if nextframe.heuristicUnsolvable():
                    continue
                if self._memo.find(nextframe):
                    continue
                self._stack.append(nextframe)
                if nextframe.isSolved():
                    break
                newtop = True
            else:
                if newtop and limit is not None:
                    limit -= 1
                    if limit <= 0:
                        return False
                popframe = self._stack.pop()
                if popframe.framesTaken > 0:
                    self._memo.insert(popframe)
        return True

    def printStats(self):
        print "{0} visited".format(self._totalframes)
        memorates = ""
        if self._memo.inserts > 0:
            memorates = ", {0:.2%} hit, {1:.2%} return".format(\
                self._memo.hitRate, self._memo.returnRate)
        print "memo: {0} inserts".format(self._memo.inserts) + memorates

    def getFlows(self):
        return self.Frame.recoverPaths(self._stack)
