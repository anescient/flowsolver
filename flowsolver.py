#!/usr/bin/env python

from itertools import islice, izip
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

    def run(self):
        self._solver.run()

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

        class DeadEnd(Exception):
            pass

        def __init__(self, graph, headpairs, openverts):
            self._graph = graph
            self._headpairs = headpairs
            self._openverts = openverts
            self._framegen = None
            self._framestaken = 0
            self._coverstate = None

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
                openpairs = []
                for v1, v2 in self._headpairs:
                    if v1 != v2:
                        openpairs.append((v1, v2) if v1 < v2 else (v2, v1))
                self._coverstate = (frozenset(openpairs),
                                    frozenset(self._openverts))
            return self._coverstate

        def isSolved(self):
            return not self._openverts and \
                   all(v1 == v2 for v1, v2 in self._headpairs)

        def copy(self, move=None):
            frame = self.__class__(\
                self._graph, self._headpairs, self._openverts)
            if move:
                frame.applyMove(*move)
            return frame

        def applyMove(self, vidx, to):
            pairidx = vidx // 2
            subidx = vidx % 2
            self._headpairs = list(self._headpairs)
            oldpair = self._headpairs[pairidx]
            newpair = (to, oldpair[1]) if subidx == 0 else (oldpair[0], to)
            self._headpairs[pairidx] = newpair
            if newpair[0] != newpair[1]:
                self._openverts = self._openverts.copy()
                self._openverts.remove(to)

        def _connectableAndCovered(self):
            """
                Return True iff all pairs can be connected and
                all open vertices can be reached by some pair.
            """
            components = self._graph.disjointPartitions(self._openverts)
            covered = set()
            for v1, v2 in self._headpairs:
                if v1 == v2:
                    continue
                acis1 = self._adjacentComponentIndices(components, v1)
                acis2 = self._adjacentComponentIndices(components, v2)
                commonacis = acis1.intersection(acis2)
                if not commonacis and not self._graph.adjacent(v1, v2):
                    return False
                covered |= commonacis
            return len(covered) == len(components)

        def _adjacentComponentIndices(self, components, v):
            acis = set()
            adj = self._graph.adjacencies(v)
            for ci, component in enumerate(components):
                if component.intersection(adj):
                    acis.add(ci)
            return acis

        def _hasDeadEnd(self):
            """
                Returns True iff any open vertex is adjacent only to
                one other open vertex or path head.
            """
            heads = set()
            for v1, v2 in self._headpairs:
                if v1 != v2:
                    heads.add(v1)
                    heads.add(v2)
            active = heads.union(self._openverts)
            for ov in self._openverts:
                x = len(self._graph.adjacencies(ov, active))
                assert x > 0
                if x == 1:
                    return True
            return False

        def takeNextFrame(self):
            if self._framegen is None:
                try:
                    self._framegen = self._nextFrames()
                except self.DeadEnd:
                    self._framegen = iter([])
            f = next(self._framegen, None)
            if f:
                self._framestaken += 1
            return f

        def _nextFrames(self):
            if not self._connectableAndCovered():
                raise self.DeadEnd()
            if self._hasDeadEnd():
                raise self.DeadEnd()

            movesets = self._possibleMoves()
            best = None
            for vidx, moves in movesets.iteritems():
                if best is None or len(moves) < len(best[1]):
                    best = (vidx, moves)
                if len(moves) == 1:
                    break

            if len(best[1]) > 1:
                lm = self._leafMoves(movesets)
                if lm:
                    return (self.copy(move) for move in lm)
            return (self.copy((best[0], to)) for to in best[1])

        def _possibleMoves(self):
            moves = {}  # vidx : set of vertices to move to
            for pairidx, hp in enumerate(self._headpairs):
                v1, v2 = hp
                if v1 == v2:
                    continue
                m1 = self._graph.adjacencies(v1, self._openverts)
                m2 = self._graph.adjacencies(v2, self._openverts)
                if self._graph.adjacent(v1, v2):
                    m1.add(v2)
                    m2.add(v1)
                if not m1 or not m2:
                    raise self.DeadEnd()
                moves[2 * pairidx] = m1
                moves[2 * pairidx + 1] = m2
            if not moves:
                raise self.DeadEnd()
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
            openverts = set(graph.vertices)
            openverts -= set(v for vp in endpointpairs for v in vp)
            return cls(graph, list(endpointpairs), openverts)

        @staticmethod
        def recoverPaths(framestack):
            if not framestack:
                return []
            pathpairs = [([v1], [v2]) for v1, v2 in framestack[0].headPairs]
            for frame in framestack[1:]:
                for vp, pathpair in izip(frame.headPairs, pathpairs):
                    for v, path in izip(vp, pathpair):
                        if path[-1] != v:
                            path.append(v)
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

    def run(self):
        if self.done:
            return
        newtop = False
        while self._stack:
            nextframe = self._stack[-1].takeNextFrame()
            if nextframe:
                self._totalframes += 1
                if self._memo.find(nextframe):
                    continue
                self._stack.append(nextframe)
                if nextframe.isSolved():
                    break
                newtop = True
            else:
                if newtop:
                    return
                popframe = self._stack.pop()
                if popframe.framesTaken > 0:
                    self._memo.insert(popframe)

        print "{0} visited".format(self._totalframes)
        print "memo: {0:.2%} hit, {1:.2%} return".format(\
            self._memo.hitRate, self._memo.returnRate)

    def getFlows(self):
        return self.Frame.recoverPaths(self._stack)
