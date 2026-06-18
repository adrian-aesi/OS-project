# deadlock/deadlock_manager.py — Banker's Algorithm + Deadlock Detection backend
#
# Pure logic — zero GUI code. Ported from deadlock.py (logic unchanged).
# Import this from gui/deadlock_screen.py.

# ============================================================
# Banker's Algorithm logic
# ============================================================
R = ['A', 'B', 'C']
N = 5

DA  = [[0,1,0],[2,0,0],[3,0,2],[2,1,1],[0,0,2]]
DM  = [[7,5,3],[3,2,2],[9,0,2],[2,2,2],[4,3,3]]
DAV = [3, 3, 2]

DDA  = [[0,1,0],[2,0,0],[3,0,3],[2,1,1],[0,0,2]]
DDR  = [[0,0,0],[2,0,2],[0,0,0],[1,0,0],[0,0,2]]
DDAV = [0, 0, 0]


def clone_matrix(m):
    return [row[:] for row in m]


def vec_str(v):
    return '[' + ' '.join(str(x) for x in v) + ']'


def safety(alloc, mx, avail):
    need = [[mx[i][j] - alloc[i][j] for j in range(3)] for i in range(N)]
    work = avail[:]
    finish = [False] * N
    seq = []
    step_map = {}
    progress = True
    while progress:
        progress = False
        for i in range(N):
            if not finish[i] and all(need[i][j] <= work[j] for j in range(3)):
                work_before = work[:]
                work = [work[j] + alloc[i][j] for j in range(3)]
                finish[i] = True
                seq.append(i)
                step_map[i] = {"before": work_before, "after": work[:]}
                progress = True
    return {"safe": all(finish), "seq": seq, "step_map": step_map,
            "need": need, "finish": finish}


def detect(alloc, req, avail):
    work = avail[:]
    finish = [all(v == 0 for v in alloc[i]) for i in range(N)]
    seq = []
    steps = []
    progress = True
    while progress:
        progress = False
        for i in range(N):
            if not finish[i] and all(req[i][j] <= work[j] for j in range(3)):
                work_before = work[:]
                work = [work[j] + alloc[i][j] for j in range(3)]
                finish[i] = True
                seq.append(i)
                steps.append({"proc": i, "before": work_before, "after": work[:]})
                progress = True
    dead = [i for i in range(N) if not finish[i]]
    return {"dead": dead, "seq": seq, "steps": steps}


# ============================================================
# RAG / Wait-For Graph cycle detection
# ============================================================

def detect_cycle(graph):
    """
    DFS-based cycle detection on an adjacency-list graph: {node: [neighbors]}.
    Returns a list of node ids forming the cycle, or [] if acyclic.
    Logic ported unchanged from RagWfgTab.detect() in deadlock.py.
    """
    visited   = {}
    rec_stack = {}
    cycle_nodes = []

    def dfs(node, path):
        visited[node]   = True
        rec_stack[node] = True
        for nb in graph.get(node, []):
            if not visited.get(nb):
                if dfs(nb, path + [nb]):
                    return True
            elif rec_stack.get(nb):
                if nb in path:
                    cycle_nodes.extend(path[path.index(nb):])
                else:
                    cycle_nodes.append(nb)
                return True
        rec_stack[node] = False
        return False

    for n in list(graph.keys()):
        if not visited.get(n):
            if dfs(n, [n]):
                return cycle_nodes
    return []
