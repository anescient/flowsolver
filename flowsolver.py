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
            bestvidx = None
            bestmoves = None
            for vidx in xrange(len(self._headpairs) * 2):
                moves = self._movesForVertex(vidx)
                if moves is None:
                    continue
                if len(moves) == 0:
                    raise self.DeadEnd()
                if bestmoves is None or len(moves) < len(bestmoves):
                    bestvidx = vidx
                    bestmoves = moves
            if bestvidx is None:
                return
            if len(bestmoves) > 1:
                lm = self._leafMoves()
                if lm:
                    return (self._frameForMove(vidx, m) for vidx, m in lm)
            return (self._frameForMove(bestvidx, m) for m in bestmoves)

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

        def _movesForVertex(self, vidx):
            hp = self._headpairs[vidx // 2]
            subidx = vidx % 2
            v, vother = hp[subidx], hp[1 - subidx]
            if v == vother:
                return None
            adj = self._graph.adjacencies(v)
            moves = adj.intersection(self._openverts)
            if vother in adj:
                moves.add(vother)
            return moves

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

    def __init__(self, graph, endpointpairs):
        assert all(len(vp) == 2 for vp in endpointpairs)
        assert len(reduce(set.union, map(set, endpointpairs), set())) == \
               2 * len(endpointpairs)
        openverts = set(graph.vertices)
        openverts -= set(v for vp in endpointpairs for v in vp)
        self._stack = [self.Frame(graph, list(endpointpairs), openverts)]
        self._totalframes = 1
        self._memo = set()

    @property
    def done(self):
        return not self._stack or self._stack[-1].isSolved()

    def run(self):
        if self.done:
            return
        newtop = False
        while self._stack:
            top = self._stack[-1]
            nextframe = top.takeNextFrame()
            if nextframe:
                self._totalframes += 1
                u = nextframe.getUnique()
                if u in self._memo:
                    continue
                self._memo.add(u)
                self._stack.append(nextframe)
                if nextframe.isSolved():
                    break
                newtop = True
            else:
                self._stack.pop()
                if newtop:
                    return

        print "{0} visited".format(self._totalframes)
        print "{0} memoized".format(len(self._memo))

    def getFlows(self):
        return self.Frame.recoverPaths(self._stack)
