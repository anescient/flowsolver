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
            ((v1, v2) for _, v1, v2 in self._endpoints))

    def run(self, steps=None):
        self._solver.run(steps)

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
        def __init__(self, graph, vertexpairs, freeverts):
            self._graph = graph
            self._vertexpairs = vertexpairs
            self._freeverts = freeverts
            self._framegen = self._nextFrames()

        @property
        def vertexPairs(self):
            return (vp for vp in self._vertexpairs)

        def isSolved(self):
            return not self._freeverts and \
                   all(v1 == v2 for v1, v2 in self._vertexpairs)

        def takeNextFrame(self):
            return next(self._framegen, None)

        def _nextFrames(self):
            bestvidx = None
            bestmoves = None
            for vidx in xrange(len(self._vertexpairs) * 2):
                moves = self._movesForVertex(vidx)
                if moves is None:
                    continue
                if len(moves) == 0:
                    return
                if bestmoves is None or len(moves) < len(bestmoves):
                    bestvidx = vidx
                    bestmoves = moves
            if bestvidx is None:
                return
            pairidx = bestvidx // 2
            subidx = bestvidx % 2
            nextpairs = list(self._vertexpairs)
            oldpair = nextpairs[pairidx]
            for m in bestmoves:
                newpair = (m, oldpair[1]) if subidx == 0 else (oldpair[0], m)
                nextpairs[pairidx] = newpair
                nextfree = set(self._freeverts)
                if newpair[0] != newpair[1]:
                    nextfree.remove(m)
                yield FlowGraphSolver.Frame(self._graph, nextpairs, nextfree)

        def _movesForVertex(self, vidx):
            pairidx = vidx // 2
            subidx = vidx % 2
            v = self._vertexpairs[pairidx][subidx]
            vother = self._vertexpairs[pairidx][1 - subidx]
            if v == vother:
                return None
            adj = self._graph.adjacencies(v)
            moves = adj.intersection(self._freeverts)
            if vother in adj:
                moves.add(vother)
            return moves

        @staticmethod
        def recoverPaths(framestack):
            if not framestack:
                return []
            pathpairs = [([v1], [v2]) for v1, v2 in framestack[0].vertexPairs]
            for frame in framestack[1:]:
                for vp, pathpair in zip(frame.vertexPairs, pathpairs):
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

    def __init__(self, graph, vertexpairs):
        self._graph = graph
        self._vertexpairs = list(vertexpairs)
        assert all(len(vp) == 2 for vp in self._vertexpairs)
        assert len(reduce(set.union, map(set, self._vertexpairs), set())) == \
               2 * len(self._vertexpairs)
        self._flows = None

    def run(self, steps=None):
        freeverts = set(self._graph.vertices)
        for vp in self._vertexpairs:
            for v in vp:
                freeverts.remove(v)
        stack = [FlowGraphSolver.Frame(\
            self._graph, list(self._vertexpairs), freeverts)]
        while stack:
            if steps is not None:
                if steps < 1:
                    break
                steps -= 1

            if stack[-1].isSolved():
                break
            nextframe = stack[-1].takeNextFrame()
            if nextframe:
                stack.append(nextframe)
            else:
                stack.pop()
        self._flows = FlowGraphSolver.Frame.recoverPaths(stack)
        self._flows = [f for f in self._flows if len(f) > 1]

    def getFlows(self):
        return self._flows or []
