#!/usr/bin/env python

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
            try:
                self._framegen = self._nextFrames()
            except self.DeadEnd:
                self._framegen = iter([])

        @property
        def headPairs(self):
            return (hp for hp in self._headpairs)

        def getUnique(self):
            values = []
            for v1, v2 in self._headpairs:
                if v1 == v2:
                    values.append(None)
                    values.append(None)
                elif v1 < v2:  # todo determine whether this actually matters
                               # i.e. whether both cases are possible
                    values.append(v1)
                    values.append(v2)
                else:
                    values.append(v2)
                    values.append(v1)
            values.extend(self._openverts)
            return tuple(values)

        def isSolved(self):
            return not self._openverts and \
                   all(v1 == v2 for v1, v2 in self._headpairs)

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
                adj = self._graph.adjacencies(ov)
                x = len(adj.intersection(active))
                assert x > 0
                if x == 1:
                    return True
            return False

        def takeNextFrame(self):
            return next(self._framegen, None)

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
                lm = self._leafMoves()
                if lm:
                    return (self._frameForMove(vidx, m) for vidx, m in lm)
            return (self._frameForMove(best[0], m) for m in best[1])

        def _possibleMoves(self):
            moves = {}  # vidx : set of vertices to move to
            for pairidx, hp in enumerate(self._headpairs):
                v1, v2 = hp
                if v1 == v2:
                    continue
                m1 = self._graph.adjacencies(v1) & self._openverts
                m2 = self._graph.adjacencies(v2) & self._openverts
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

        def _frameForMove(self, vidx, move):
            pairidx = vidx // 2
            subidx = vidx % 2
            nextpairs = list(self._headpairs)
            oldpair = nextpairs[pairidx]
            newpair = (move, oldpair[1]) if subidx == 0 else (oldpair[0], move)
            nextpairs[pairidx] = newpair
            nextfree = set(self._openverts)
            if newpair[0] != newpair[1]:
                nextfree.remove(move)
            return self.__class__(self._graph, nextpairs, nextfree)

        def _leafMoves(self):
            """return list of (vidx, move) or None"""
            d = {}  # open v : set of vidx
            for vidx in xrange(len(self._headpairs) * 2):
                hp = self._headpairs[vidx // 2]
                subidx = vidx % 2
                v, vother = hp[subidx], hp[1 - subidx]
                if v == vother:
                    continue
                o = self._graph.adjacencies(v).intersection(self._openverts)
                for ov in o:
                    if ov not in d:
                        d[ov] = set()
                    d[ov].add(vidx)
            for ov, vidxset in d.iteritems():
                lov = len(self._graph.adjacencies(ov)\
                          .intersection(self._openverts))
                if lov == 1:
                    return [(vidx, ov) for vidx in vidxset]
            return None

        @staticmethod
        def recoverPaths(framestack):
            if not framestack:
                return []
            pathpairs = [([v1], [v2]) for v1, v2 in framestack[0].headPairs]
            for frame in framestack[1:]:
                for vp, pathpair in zip(frame.headPairs, pathpairs):
                    for v, path in zip(vp, pathpair):
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
            self._hits = 0
            self._limit = 20000

        def insert(self, frame):
            if len(self._memo) >= self._limit:
                self._prune(3 * self._limit // 4)
            self._memo[frame.getUnique()] = 0

        def find(self, frame):
            u = frame.getUnique()
            hit = u in self._memo
            if hit:
                self._hits += 1
                self._memo[u] = self._hits
            return hit

        def _prune(self, limit):
            elms = sorted(self._memo, key=self._memo.get, reverse=True)
            prunememo = {}
            for e in elms[:limit]:
                prunememo[e] = self._memo[e]
            self._memo = prunememo

    def __init__(self, graph, endpointpairs):
        assert all(len(vp) == 2 for vp in endpointpairs)
        assert len(reduce(set.union, map(set, endpointpairs), set())) == \
               2 * len(endpointpairs)
        openverts = set(graph.vertices)
        openverts -= set(v for vp in endpointpairs for v in vp)
        self._stack = [self.Frame(graph, list(endpointpairs), openverts)]
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
                self._memo.insert(self._stack.pop())
                if newtop:
                    return

        print "{0} visited".format(self._totalframes)

    def getFlows(self):
        return self.Frame.recoverPaths(self._stack)
