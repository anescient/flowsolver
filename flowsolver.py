#!/usr/bin/env python

from collections import deque
from itertools import islice, chain, izip
from flowboard import FlowBoardGraph


class FlowGraphSolver(object):

    class _Frame(object):

        def __init__(self, graph, headpairs, \
                     openverts, components, commoncomponents):
            self._graph = graph
            self._headpairs = headpairs
            self._openverts = openverts
            self._components = components
            self._commoncomponents = commoncomponents
            self._nextframes = None
            self._aborted = False
            self._coverstate = None
            self._moveapplied = None

        @property
        def moveApplied(self):
            return self._moveapplied

        @property
        def headPairs(self):
            return iter(self._headpairs)

        @property
        def hasNext(self):
            if self.aborted:
                return False
            if self._nextframes is None:
                self._generateNextFrames()
            return len(self._nextframes) > 0

        @property
        def aborted(self):
            return self._aborted

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

            if len(self._components) > 1:
                # if any component is usable by only one pair,
                # commit that pair to that component
                componentusers = dict((k, set()) for k in self._components)
                for i, cc in enumerate(self._commoncomponents):
                    for k in cc:
                        componentusers[k].add(i)
                commit = True
                while commit:
                    commit = None
                    for k, users in componentusers.iteritems():
                        if len(users) == 1:
                            commit = (next(iter(users)), k)
                            break
                    if commit:
                        i, k = commit
                        if len(self._commoncomponents[i]) > 1:
                            for k_ in self._commoncomponents[i]:
                                componentusers[k_].remove(i)
                            self._commoncomponents[i] = set([k])
                        del componentusers[k]

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

        def biconnectedUnsolvable(self):
            for k, component in self._components.iteritems():
                bcs, seps = self._graph.biconnectedComponents(component)
                if not seps:
                    continue

                # check if any biconnected component cannot be covered
                leafbcis = set()
                for i, bc in enumerate(bcs):
                    if len(bc & seps) == 1:
                        leafbcis.add(i)
                for i in leafbcis:
                    bc = bcs[i]
                    for pairi, (v1, v2) in enumerate(self._headpairs):
                        if k not in self._commoncomponents[pairi]:
                            continue
                        adj1 = self._graph.adjacencies(v1)
                        if adj1 & bc:
                            break
                        adj2 = self._graph.adjacencies(v2)
                        if adj2 & bc:
                            break
                    else:
                        return True

                # check if any cut vertex must be used by more than one pair
                sepconflicts = set()
                for pairi, (v1, v2) in enumerate(self._headpairs):
                    if k not in self._commoncomponents[pairi]:
                        continue
                    if len(self._commoncomponents[pairi]) > 1:
                        continue
                    adj1 = self._graph.adjacencies(v1)
                    adj2 = self._graph.adjacencies(v2)
                    bcis1 = set(i for i, bc in enumerate(bcs) if adj1 & bc)
                    bcis2 = set(i for i, bc in enumerate(bcs) if adj2 & bc)
                    if bcis1 & bcis2:
                        continue
                    p = set(self._graph.shortestPath(v1, v2, component))
                    ends = reduce(set.union, (bcs[i] for i in (bcis1 | bcis2)))
                    must = (p & seps) - ends
                    if must & sepconflicts:
                        return True
                    sepconflicts.update(must)
            return False

        def takeNextFrame(self):
            assert not self.aborted
            if self._nextframes is None:
                self._generateNextFrames()
            return self._nextframes.popleft()

        def abort(self):
            assert self._nextframes is None
            self._aborted = True

        def _generateNextFrames(self):
            assert self._nextframes is None
            if not self._headpairs:
                self._nextframes = []
                return
            movesets = self._possibleMoves()
            msit = movesets.iteritems()
            best = next(msit)
            for vidx, moves in msit:
                if len(best[1]) == 1:
                    break
                if len(moves) < len(best[1]):
                    best = (vidx, moves)

            if len(best[1]) > 1:
                leafmoves = self._leafMoves(movesets)
                if leafmoves:
                    self._nextframes = \
                        deque(self.copy(move) for move in leafmoves)
                    return

            # this sort tends to lead to less convoluted paths in solution
            vidx = best[0]
            moves = sorted(best[1], \
                key=lambda v: len(self._graph.adjacencies(v, self._openverts)))
            self._nextframes = \
                deque(self.copy((vidx, to)) for to in moves)

        def _possibleMoves(self):
            moves = {}  # vidx : set of vertices to move to
            for pairidx, (v1, v2) in enumerate(self._headpairs):
                common = self._commoncomponents[pairidx]
                if common:
                    openverts = reduce(set.union, \
                        map(self._components.get, common))
                    m1 = self._graph.adjacencies(v1, openverts)
                    m2 = self._graph.adjacencies(v2, openverts)
                    if self._graph.adjacent(v1, v2):
                        m1.add(v2)
                        m2.add(v1)
                    assert m1 and m2
                else:
                    assert self._graph.adjacent(v1, v2)
                    m1 = set([v2])
                    m2 = set([v1])
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

    class _Memo(object):
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
        self._stack = [self._Frame.initial(graph, endpointpairs)]
        if self._stack[-1].heuristicUnsolvable():
            self._stack = []
        self._totalframes = 1
        self._memo = self._Memo()

    @property
    def done(self):
        return not self._stack or self._stack[-1].isSolved()

    @property
    def solved(self):
        return self._stack and self._stack[-1].isSolved()

    def step(self):
        if not self._stack:
            return False
        while self._stack[-1].hasNext:
            top = self._stack[-1].takeNextFrame()
            self._stack.append(top)
            self._totalframes += 1
            if top.heuristicUnsolvable() or self._memo.find(top):
                top.abort()
                return False
            if top.biconnectedUnsolvable():
                self._memo.insert(top)
                top.abort()
                return False
            return True
        return False

    def stepBack(self):
        if not self._stack:
            return False
        if self._stack[-1].hasNext:
            return False
        popped = self._stack.pop()
        if not popped.aborted:
            self._memo.insert(popped)
        return True

    def run(self, limit=None):
        if self.done:
            return True
        while self._stack:
            step = False
            while self.step():
                step = True
            if self._stack[-1].isSolved():
                return True
            if step and limit is not None:
                limit -= 1
                if limit <= 0:
                    return False
            while self.stepBack():
                pass
        return True

    def printStats(self):
        print "{0} visited".format(self._totalframes)
        memorates = ""
        if self._memo.inserts > 0:
            memorates = ", {0:.2%} hit, {1:.2%} return".format(\
                self._memo.hitRate, self._memo.returnRate)
        print "memo: {0} inserts".format(self._memo.inserts) + memorates
        if self.solved:
            flows = []
            for f in self.__getFlows():
                if f[0] > f[-1]:
                    f.reverse()
                flows.append(tuple(f))
            print "solution", hex(abs(hash(frozenset(flows))))

    def getFlows(self):
        return self._Frame.recoverPaths(self._stack)

    __getFlows = getFlows


class FlowBoardSolver(FlowGraphSolver):
    def __init__(self, board):
        assert board.isValid()
        self._boardgraph = FlowBoardGraph(board)

        self._vertexKey = {}
        endpointpairs = []
        for k, (xy1, xy2) in board.endpointPairs:
            v1 = self._boardgraph.cellToVertex(xy1)
            v2 = self._boardgraph.cellToVertex(xy2)
            self._vertexKey[v1] = k
            self._vertexKey[v2] = k
            endpointpairs.append((v1, v2))

        super(FlowBoardSolver, self).__init__(self._boardgraph, endpointpairs)

    def getFlows(self):
        for vflow in super(FlowBoardSolver, self).getFlows():
            yield (self._vertexKey[vflow[0]], \
                   self._boardgraph.verticesToCells(vflow))
