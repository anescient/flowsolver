#!/usr/bin/env python

from itertools import product
from graph import SimpleGraph


class GraphOntoRectangularGrid(object):
    """
        Locations in the grid are tuples (x, y), 0-based.
        Each vertex maps to one grid location.
        It is possible for a grid location to map to multiple vertices.
    """

    def __init__(self, width, height=None):
        height = height or width
        assert width > 0 and height > 0
        self._width = width
        self._height = height
        self._graph = SimpleGraph()
        self._locationMap = {}  # vertex : location
        for x, y in product(range(self._width), range(self._height)):
            v = self.pushVertex((x, y))
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

    @property
    def graph(self):
        return self._graph.asReadOnly()

    def getLocationMap(self):
        return dict((v, tuple(c)) for v, c in self._locationMap.items())

    def pushVertex(self, xy):
        x, y = xy
        assert x >= 0 and x < self._width
        assert y >= 0 and y < self._height
        v = self._graph.pushVertex()
        self._locationMap[v] = xy
        return v

    def removeVertex(self, v):
        self._graph.removeVertex(v)
        del self._locationMap[v]

    def removeVertexAt(self, xy):
        self.removeVertex(self.singleVertexAt(xy))

    def addEdge(self, v1, v2):
        self._graph.addEdge(v1, v2)

    def removeUniqueEdge(self, xy1, xy2):
        v1, v2 = map(self.singleVertexAt, (xy1, xy2))
        self._graph.removeEdge(v1, v2)

    def verticesAt(self, xy):
        """Get the set of any/all vertices mapped to location."""
        return set(k for k, v in self._locationMap.items() if v == xy)

    def singleVertexAt(self, xy):
        """Get the single vertex mapped to location. Error if not 1-to-1."""
        v = self.verticesAt(xy)
        assert len(v) == 1
        return v.pop()

    def adjacenciesAt(self, xy):
        return self._graph.adjacencies(self.singleVertexAt(xy))

    def orthogonalAdjacencies(self, xy):
        x, y = xy
        a = self.adjacenciesAt(xy)
        xa = a & (self.verticesAt((x - 1, y)) | self.verticesAt((x + 1, y)))
        ya = a & (self.verticesAt((x, y - 1)) | self.verticesAt((x, y + 1)))
        return xa, ya
