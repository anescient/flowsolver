#!/usr/bin/env python


class FlowSolver(object):
    def __init__(self, board):
        self._board = board

    def run(self):
        pass

    def getFlows(self):
        for key, start, end in self._board.endpointPairs:
            flow = [start]
            while flow[-1][0] < end[0]:
                flow.append((flow[-1][0] + 1, flow[-1][1]))
            while flow[-1][0] > end[0]:
                flow.append((flow[-1][0] - 1, flow[-1][1]))
            while flow[-1][1] < end[1]:
                flow.append((flow[-1][0], flow[-1][1] + 1))
            while flow[-1][1] > end[1]:
                flow.append((flow[-1][0], flow[-1][1] - 1))
            yield (key, flow)
