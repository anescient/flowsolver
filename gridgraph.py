#!/usr/bin/env python

from copy import deepcopy
from graph import SimpleGraph


class GraphOntoRectangularGrid(object):
    """
        Locations in the grid are tuples (x, y), 0-based.
        Each vertex maps to one grid location.
        It is possible for a grid location to map to multiple vertices.
        All in-range locations map to at least one vertex.
    """

    def __init__(self, width, height=None):
        height = height or width
        assert width > 0 and height > 0
        self._width = width
        self._height = height
        self._graph = SimpleGraph()
        self._locationMap = {}  # vertex : location
        for x in xrange(self._width):
            for y in xrange(self._height):
                v = self._graph.pushVertex()
                self._locationMap[v] = (x, y)
                if x > 0:
                    self._graph.addEdge(v, self.singleVertexAt((x - 1, y)))
                if y > 0:
                    self._graph.addEdge(v, self.singleVertexAt((x, y - 1)))

    @property
    def width(self):
        return self._width

    @property
    def height(self):
        return self._height

    def getGraphCopy(self):
        """Return a copy of the current state of the graph."""
        return deepcopy(self._graph)

    def verticesAt(self, xy):
        """Get the set of any/all vertices mapped to location."""
        return set(k for k, v in self._locationMap.iteritems() if v == xy)

    def singleVertexAt(self, xy):
        """Get the single vertex mapped to location. Error if not 1-to-1."""
        v = self.verticesAt(xy)
        assert len(v) == 1
        return v.pop()

    def locationForVertex(self, v):
        return self._locationMap[v]

    def addBridge(self, xy):
        """
            Location must have single vertex and four neighbors.
            Split the vertex joining four neighbors into two vertices
            joining left-right and up-down neighbors respectively.
        """
        v = self.singleVertexAt(xy)
        x, y = xy
        assert x > 0 and x < self._width - 1
        assert y > 0 and y < self._height - 1

        adjacent = self._graph.adjacencies(v)
        x_adj = adjacent.intersection(\
            self.verticesAt((x - 1, y)).union(\
            self.verticesAt((x + 1, y))))
        y_adj = adjacent.intersection(\
            self.verticesAt((x, y - 1)).union(\
            self.verticesAt((x, y + 1))))
        assert len(x_adj) == 2 and len(y_adj) == 2

        self._graph.removeVertex(v)
        del self._locationMap[v]

        xpass = self._graph.pushVertex()
        self._graph.addEdge(x_adj.pop(), xpass)
        self._graph.addEdge(x_adj.pop(), xpass)
        self._locationMap[xpass] = xy

        ypass = self._graph.pushVertex()
        self._graph.addEdge(y_adj.pop(), ypass)
        self._graph.addEdge(y_adj.pop(), ypass)
        self._locationMap[ypass] = xy
