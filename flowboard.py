#!/usr/bin/env python

from gridgraph import GraphOntoRectangularGrid
from flowsolver import FlowPuzzle, FlowSolver


class FlowBoard(object):
    def __init__(self, size=None):
        self._size = size or 7
        self._endpoints = {}  # key: list (length 1 or 2) of 2-tuples
        self._bridges = set()  # 2-tuples
        self._blockages = set()  # 2-tuples

    @property
    def size(self):
        return self._size

    @property
    def endpoints(self):
        for k, l in self._endpoints.iteritems():
            for cell in l:
                yield (cell, k)

    @property
    def endpointPairs(self):
        for k, l in self._endpoints.iteritems():
            assert self.hasCompleteEndpoints(k)
            yield (k, tuple(l))

    @property
    def bridges(self):
        return iter(self._bridges)

    @property
    def blockages(self):
        return iter(self._blockages)

    def isEmpty(self):
        return not (self._endpoints or self._bridges or self._blockages)

    def isValid(self):
        if not self._endpoints:
            return False
        if not all(self.hasCompleteEndpoints(k) for k in self._endpoints):
            return False
        if not all(self.bridgeValidAt(cell) for cell in self._bridges):
            return False
        if not all(self.blockageValidAt(cell) for cell in self._blockages):
            return False
        if self._bridges and len(self._endpoints) < 2:
            return False
        return True

    def hasCompleteEndpoints(self, key):
        return key in self._endpoints and len(self._endpoints[key]) == 2

    def nextEndpointDrop(self, key):
        if key in self._endpoints and len(self._endpoints[key]) == 2:
            return self._endpoints[key][0]
        return None

    def setEndpoint(self, cell, key):
        self.clear(cell)
        l = self._endpoints[key] if key in self._endpoints else []
        l.append(cell)
        if len(l) > 2:
            l = l[-2:]
        self._endpoints[key] = l

    def endpointKeyAt(self, cell):
        assert self._includesCell(cell)
        for k, l in self._endpoints.iteritems():
            if cell in l:
                return k
        return None

    def bridgeValidAt(self, cell):
        return len(self._adjacentUnblockedCells(cell)) == 4

    def setBridge(self, cell):
        assert self.bridgeValidAt(cell)
        self.clear(cell)
        self._bridges.add(cell)

    def hasBridgeAt(self, cell):
        return cell in self._bridges

    def blockageValidAt(self, cell):
        return not self._bridges.intersection(self._adjacentCells(cell))

    def setBlockage(self, cell):
        assert self.blockageValidAt(cell)
        self.clear(cell)
        self._blockages.add(cell)

    def hasBlockageAt(self, cell):
        return cell in self._blockages

    def isClear(self, cell):
        if cell in self._bridges or cell in self._blockages:
            return False
        return not any(cell in cells for cells in self._endpoints.values())

    def clear(self, cell):
        assert self._includesCell(cell)
        for k, l in self._endpoints.iteritems():
            if cell in l:
                l.remove(cell)
                if not l:
                    del self._endpoints[k]
                break
        self._bridges.discard(cell)
        self._blockages.discard(cell)

    def getPuzzle(self):
        """
            Return (FlowPuzzle, dict)
            The dictionary is a mapping of vertex to cell coordinates.
        """
        gridgraph = GraphOntoRectangularGrid(self.size)

        endpointPairs = []
        for _, xypair in self.endpointPairs:
            vpair = tuple(map(gridgraph.singleVertexAt, xypair))
            endpointPairs.append(vpair)

        for xy in self.blockages:
            gridgraph.removeVertexAt(xy)

        exclusiveSets = []
        for xy in self.bridges:
            x_adj, y_adj = gridgraph.orthogonalAdjacencies(xy)
            assert len(x_adj) == 2 and len(y_adj) == 2
            gridgraph.removeVertexAt(xy)

            xpass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(x_adj.pop(), xpass)
            gridgraph.addEdge(x_adj.pop(), xpass)

            ypass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(y_adj.pop(), ypass)
            gridgraph.addEdge(y_adj.pop(), ypass)

            exclusiveSets.append(set([xpass, ypass]))

        return (FlowPuzzle(gridgraph.graph, endpointPairs, exclusiveSets),
                gridgraph.getLocationMap())

    def _includesCell(self, cell):
        return 0 <= cell[0] < self.size and 0 <= cell[1] < self.size

    def _adjacentUnblockedCells(self, cell):
        return set(self._adjacentCells(cell)) - self._blockages

    def _adjacentCells(self, cell):
        if cell[0] > 0:
            yield (cell[0] - 1, cell[1])
        if cell[0] < self._size - 1:
            yield (cell[0] + 1, cell[1])
        if cell[1] > 0:
            yield (cell[0], cell[1] - 1)
        if cell[1] < self._size - 1:
            yield (cell[0], cell[1] + 1)


class FlowBoardSolver(FlowSolver):
    def __init__(self, board):
        assert board.isValid()
        puzzle, self._cellmap = board.getPuzzle()
        super(FlowBoardSolver, self).__init__(puzzle)

        self._vertexKey = {}
        for v1, v2 in puzzle.endpointPairs:
            k = board.endpointKeyAt(self._cellmap[v1])
            assert board.endpointKeyAt(self._cellmap[v2]) == k
            self._vertexKey[v1] = k
            self._vertexKey[v2] = k

    def getFlows(self):
        for vflow in super(FlowBoardSolver, self).getFlows():
            yield (self._vertexKey[vflow[0]], map(self._cellmap.get, vflow))
