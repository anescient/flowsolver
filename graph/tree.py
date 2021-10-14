#!/usr/bin/env python


class Tree(object):
    def __init__(self, root):
        self._root = root
        self._nodes = {root: (None, 0)}  # vertex : (parent, depth)

    @property
    def root(self):
        return self._root

    def __contains__(self, v):
        return v in self._nodes

    def add(self, v, parent):
        assert v not in self._nodes
        self._nodes[v] = (parent, self.depthOf(parent) + 1)

    def depthOf(self, v):
        return self._nodes[v][1]

    def parent(self, v):
        return self._nodes[v][0]

    def findPath(self, v, u):
        assert v in self._nodes
        assert u in self._nodes
        v_path = [v]  # path from v toward root
        u_path = [u]  # path from u toward root
        while v_path[-1] != u_path[-1]:
            advance_v = self.depthOf(v_path[-1]) > self.depthOf(u_path[-1])
            advance_u = self.depthOf(u_path[-1]) > self.depthOf(v_path[-1])
            if advance_v or not advance_u:
                v_path.append(self._nodes[v_path[-1]][0])
            if advance_u or not advance_v:
                u_path.append(self._nodes[u_path[-1]][0])
        v_path.extend(reversed(u_path[:-1]))
        return v_path

    def pathToRoot(self, v):
        v_path = [v]
        while v_path[-1] != self._root:
            v_path.append(self.parent(v_path[-1]))
        return v_path


class Forest(object):
    def __init__(self):
        self._trees = {}  # vertex : tree containing the vertex

    def __contains__(self, v):
        return v in self._trees

    def addTree(self, root):
        assert root not in self._trees
        self._trees[root] = Tree(root)

    def add(self, v, parent):
        assert v not in self._trees
        tree = self._trees[parent]
        tree.add(v, parent)
        self._trees[v] = tree

    def depthOf(self, v):
        return self._trees[v].depthOf(v)

    def rootFor(self, v):
        return self._trees[v].root

    def findPath(self, v, u):
        vtree = self._trees[v]
        if vtree is not self._trees[u]:
            return None
        return vtree.findPath(v, u)

    def pathToRoot(self, v):
        return self._trees[v].pathToRoot(v)
