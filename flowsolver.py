#!/usr/bin/env python

from collections import deque
from itertools import islice, chain, izip, product
from graph import OnlineReducedGraph


class FlowPuzzle(object):
    def __init__(self, graph, endpointPairs, exclusiveSets):
        self._graph = graph
        self._endpointPairs = endpointPairs
        self._exclusiveSets = exclusiveSets
        self._exclusionMap = {}
        for es in self._exclusiveSets:
            assert len(es) > 1
            for v in es:
                if v not in self._exclusionMap:
                    self._exclusionMap[v] = set()
                self._exclusionMap[v] |= es
        for v, es in self._exclusionMap.iteritems():
            es.remove(v)

    @property
    def graph(self):
        return self._graph

    @property
    def endpointPairs(self):
        """2-tuples of vertices to be connected."""
        return iter(self._endpointPairs)

    @property
    def exclusiveSets(self):
        """Sets of vertices. A path may include at most one from each set."""
        return iter(self._exclusiveSets)

    def exclusions(self, v):
        return self._exclusionMap.get(v, None)


class FlowSolver(object):

    class _Frame(object):

        def __init__(self, puzzle, reducedgraph, \
                           headpairs, commoncomponents, blocks):
            self._puzzle = puzzle
            self._graph = self._puzzle.graph
            self._reducedgraph = reducedgraph
            self._headpairs = headpairs
            self._commoncomponents = commoncomponents
            self._blocks = blocks
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
                headstate = []
                for hp, blocks in izip(self._headpairs, self._blocks):
                    headstate.append((hp, tuple(blocks)) if blocks else hp)
                headstate = frozenset(headstate)
                self._coverstate = \
                    (headstate, frozenset(self._reducedgraph.vertices))
            return self._coverstate

        def isSolved(self):
            return self._reducedgraph.allMasked and not self._headpairs

        def copy(self, move=None):
            frame = self.__class__(self._puzzle, self._reducedgraph, \
                                   self._headpairs, self._commoncomponents, \
                                   self._blocks)
            if move:
                frame.applyMove(*move)
            return frame

        def applyMove(self, vidx, to):
            assert self._moveapplied is None
            pairidx, subidx = divmod(vidx, 2)
            oldpair = self._headpairs[pairidx]
            head, other = oldpair[subidx], oldpair[1 - subidx]
            self._moveapplied = (head, to)
            self._headpairs = list(self._headpairs)
            self._commoncomponents = list(self._commoncomponents)
            if to == other:
                self._headpairs.pop(pairidx)
                self._commoncomponents.pop(pairidx)
                self._blocks = list(self._blocks)
                self._blocks.pop(pairidx)
            else:
                self._headpairs[pairidx] = \
                    (to, other) if to < other else (other, to)
                if self._puzzle.exclusions(to):
                    self._blocks = list(self._blocks)
                    self._blocks[pairidx] = \
                        self._blocks[pairidx] | self._puzzle.exclusions(to)
                self._reducedgraph = self._reducedgraph.copy()
                self._closeVertex(to)

                toadj = self._graph.adjacencies(to)
                common = None
                for k in self._commoncomponents[pairidx]:
                    if not toadj & self._reducedgraph.components[k]:
                        if common is None:
                            common = self._commoncomponents[pairidx].copy()
                        common.remove(k)
                if common is not None:
                    self._commoncomponents[pairidx] = common

            if self._reducedgraph.disjoint:
                # if any component is usable by only one pair,
                # commit that pair to that component
                componentusers = \
                    dict((k, set()) for k in self._reducedgraph.components)
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
            self._reducedgraph.maskVertex(v)
            k_deleted = self._reducedgraph.componentDeleted
            k_reduced = self._reducedgraph.componentReduced
            subcomps = self._reducedgraph.newSubComponents

            if k_reduced is not None:
                assert k_deleted is None and subcomps is None
                reduced = self._reducedgraph.components[k_reduced]
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
                            for k in subcomps:
                                c = self._reducedgraph.components[k]
                                if adj1 & c and adj2 & c:
                                    common.add(k)
                        self._commoncomponents[i] = common

        def simpleUnsolvable(self):
            # check that all pairs can be connected and
            # all open vertices can be reached by some pair
            covered = set()
            for common, (v1, v2) in izip(self._commoncomponents, \
                                         self._headpairs):
                if not common and not self._graph.adjacent(v1, v2):
                    return True
                covered |= common
            if len(covered) != len(self._reducedgraph.components):
                return True

            # check if any open vertex is adjacent only to
            # one other open vertex or one path head
            if self._moveapplied:  # assume parent frames have been checked
                checkverts = \
                    self._reducedgraph.adjacencies(self._moveapplied[0]) | \
                    self._reducedgraph.adjacencies(self._moveapplied[1])
            else:
                checkverts = self._reducedgraph.vertices
            active = self._reducedgraph.vertices.union(chain(*self._headpairs))
            for v in checkverts:
                x = len(self._graph.adjacencies(v, active))
                assert x > 0
                if x == 1:
                    return True

            return False

        def biconnectedUnsolvable(self):
            if not self._reducedgraph.separatorsChanged:
                return False  # assume parent frames have been checked
            bf, bfmap, bfseps = self._reducedgraph.blockForest()
            bf_covered = set()
            bfseps_used = set()
            for cc, (v1, v2) in izip(self._commoncomponents, self._headpairs):
                doconflict = len(cc) == 1 and not self._graph.adjacent(v1, v2)
                for c_k in cc:
                    v1_in = set(map(bfmap.get, \
                        self._reducedgraph.componentAdjacencies(v1, c_k)))
                    v2_in = set(map(bfmap.get, \
                        self._reducedgraph.componentAdjacencies(v2, c_k)))
                    pcommon = bfseps.copy() if doconflict else None
                    for a, b in product(v1_in, v2_in):
                        p = set(bf.shortestPath(a, b))
                        bf_covered |= p
                        if doconflict:
                            pcommon &= p
                    if doconflict:
                        if pcommon & bfseps_used:
                            return True
                        bfseps_used |= pcommon
            return not (set(bfmap.values()) - bfseps).issubset(bf_covered)

        def takeNextFrame(self):
            assert not self.aborted
            self._generateNextFrames()
            return self._nextframes.popleft()

        def abort(self):
            assert self._nextframes is None
            self._aborted = True

        def _generateNextFrames(self):
            if self._nextframes is None:
                self._nextframes = \
                    deque(self.copy(m) for m in self._bestMoves())

        def _bestMoves(self):
            movesets = self._possibleMoves()
            if movesets is None:
                return []
            if len(movesets) == 1:
                vidx, moves = movesets[0]
                return ((vidx, to) for to in moves)
            leafmove = self._leafMove(movesets)
            if leafmove:
                return [leafmove]

            # not sure why this helps as much as it does
            # maybe by increasing chance of memo hit?
            # re-evaluate this if memoization is significantly changed
            bcs, _ = self._reducedgraph.biconnectedComponents()
            if len(bcs) > 1:
                focus = min(bcs, key=len)
                focusmovesets = [ms for ms in movesets if ms[1] & focus]
                movesets = focusmovesets or movesets

            vidx, moves = min(movesets, key=lambda ms: len(ms[1]))
            target = self._headpairs[vidx // 2][1 - vidx % 2]
            moves = self._reducedgraph.sortClosest(moves, target)
            return ((vidx, to) for to in moves)

        def _possibleMoves(self):
            if not self._headpairs:
                return None
            movesets = []  # (vidx, set of vertices to move to)
            for pairidx, (v1, v2) in enumerate(self._headpairs):
                common = self._commoncomponents[pairidx]
                if common:
                    m1 = self._reducedgraph.componentsAdjacencies(v1, common)
                    m2 = self._reducedgraph.componentsAdjacencies(v2, common)
                    if self._blocks[pairidx]:
                        m1 -= self._blocks[pairidx]
                        m2 -= self._blocks[pairidx]
                    if self._graph.adjacent(v1, v2):
                        m1.add(v2)
                        m2.add(v1)
                    if not m1 or not m2:
                        return None
                else:
                    assert self._graph.adjacent(v1, v2)
                    m1 = set([v2])
                    m2 = set([v1])
                ms1 = (2 * pairidx, m1)
                ms2 = (2 * pairidx + 1, m2)
                if len(m1) == 1:
                    return [ms1]
                if len(m2) == 1:
                    return [ms2]
                movesets.append(ms1)
                movesets.append(ms2)
            return movesets

        def _leafMove(self, movesets):
            """return (vidx, move) or None"""
            # Look for a move to an open vertex which is adjacent only to
            # one other open vertex and one path head.
            # If such a move exists now, it must eventually be taken.
            allmoves = reduce(set.union, (moves for _, moves in movesets))
            leafs = []
            for m in allmoves.intersection(self._reducedgraph.vertices):
                if len(self._reducedgraph.adjacencies(m)) == 1:
                    leafs.append(m)
            for leaf in leafs:
                vidxs = [vidx for vidx, moves in movesets if leaf in moves]
                if len(vidxs) == 1:
                    return (vidxs[0], leaf)
            return None

        @classmethod
        def initial(cls, puzzle):
            headpairs = [tuple(sorted(ep)) for ep in puzzle.endpointPairs]
            reducedgraph = OnlineReducedGraph(puzzle.graph)
            for v in chain(*headpairs):
                reducedgraph.maskVertex(v)
            commoncomponents = []
            for v1, v2 in headpairs:
                commoncomponents.append(reducedgraph.adjacentComponents(v1) & \
                                        reducedgraph.adjacentComponents(v2))
            blocks = [set()] * len(headpairs)
            return cls(puzzle, reducedgraph, \
                       headpairs, commoncomponents, blocks)

        @staticmethod
        def recoverPaths(framestack):
            if not framestack:
                return []
            pathpairs = [([v1], [v2]) for v1, v2 in framestack[0].headPairs]
            for frame in framestack[1:]:
                for path in chain(*pathpairs):
                    if path[-1] == frame.moveApplied[0]:
                        path.append(frame.moveApplied[1])
                        break
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

        def stats(self):
            stats = "{0} inserts".format(self._inserts)
            if self._finds > 0 and self._inserts > 0:
                stats += ", {0:.2%} hit, {1:.2%} return".format(\
                    self._hits / float(self._finds), \
                    self._hits / float(self._inserts))
            return stats

        def _prune(self, limit):
            keep = islice(\
                sorted(self._memo, key=self._memo.get, reverse=True), limit)
            self._memo = dict((k, self._memo[k]) for k in keep)

    def __init__(self, puzzle):
        self._stack = [self._Frame.initial(puzzle)]
        if self._stack[-1].simpleUnsolvable():
            self._stack = []
        self._totalframes = 1
        self._memo = self._Memo()

    @property
    def done(self):
        return bool(not self._stack or self._stack[-1].isSolved())

    @property
    def solved(self):
        return bool(self._stack and self._stack[-1].isSolved())

    def stateHash(self):
        return hash(self._immutableFlows())

    def step(self):
        if not self._stack:
            return False
        while self._stack[-1].hasNext:
            top = self._stack[-1].takeNextFrame()
            self._stack.append(top)
            self._totalframes += 1
            if top.simpleUnsolvable() or self._memo.find(top):
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

    def skipSolution(self):
        assert self.solved
        while self.stepBack():
            pass
        self._memo = self._Memo()

    def printStats(self):
        print "{0} visited".format(self._totalframes)
        print "memo: " + self._memo.stats()
        if self.solved:
            print "solution", hex(abs(self.stateHash()))

    def getFlows(self):
        return self._Frame.recoverPaths(self._stack)

    def _immutableFlows(self):
        flows = []
        for flow in self.__getFlows():
            if flow[-1] < flow[0]:
                flow.reverse()
            flows.append(tuple(flow))
        return frozenset(flows)

    __getFlows = getFlows
