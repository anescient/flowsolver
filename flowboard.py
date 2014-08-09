#!/usr/bin/env python

from graph import QueryableSimpleGraph
from gridgraph import GraphOntoRectangularGrid


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

    def isValid(self):
        if not self._endpoints:
            return False
        if not all(self.hasCompleteEndpoints(k) for k in self._endpoints):
            return False
        if not all(self.bridgeValidAt(cell) for cell in self._bridges):
            return False
        if not all(self.blockageValidAt(cell) for cell in self._blockages):
            return False
        return True

    def hasCompleteEndpoints(self, key):
        return key in self._endpoints and len(self._endpoints[key]) == 2

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

    def _includesCell(self, cell):
        return cell[0] >= 0 and cell[0] < self._size and \
               cell[1] >= 0 and cell[1] < self._size

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

    @staticmethod
    def _adjacent(cell1, cell2):
        return (abs(cell1[0] - cell2[0]) == 1) != \
               (abs(cell1[1] - cell2[1]) == 1)


class FlowBoardGraph(QueryableSimpleGraph):
    def __init__(self, board):
        gridgraph = GraphOntoRectangularGrid(board.size)

        for xy in board.blockages:
            gridgraph.removeVertexAt(xy)

        for xy in board.bridges:
            x, y = xy
            v = gridgraph.singleVertexAt(xy)

            x_adj = gridgraph.adjacenciesAt(xy).intersection(\
                gridgraph.verticesAt((x - 1, y)).union(\
                gridgraph.verticesAt((x + 1, y))))
            y_adj = gridgraph.adjacenciesAt(xy).intersection(\
                gridgraph.verticesAt((x, y - 1)).union(\
                gridgraph.verticesAt((x, y + 1))))
            assert len(x_adj) == 2 and len(y_adj) == 2

            xpass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(x_adj.pop(), xpass)
            gridgraph.addEdge(x_adj.pop(), xpass)

            ypass = gridgraph.pushVertex(xy)
            gridgraph.addEdge(y_adj.pop(), ypass)
            gridgraph.addEdge(y_adj.pop(), ypass)

            gridgraph.removeVertex(v)

        self._cellToVertex = gridgraph.singleVertexAt
        self._vertexToCell = gridgraph.locationForVertex
        super(FlowBoardGraph, self).__init__(gridgraph.graph.copyEdgeSets())

    def cellToVertex(self, cell):
        return self._cellToVertex(cell)

    def vertexToCell(self, v):
        return self._vertexToCell(v)

    def verticesToCells(self, vseq):
        return list(map(self._vertexToCell, vseq))
