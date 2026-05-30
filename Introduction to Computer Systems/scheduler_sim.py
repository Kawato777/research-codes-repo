import random
from dataclasses import dataclass
from typing import Optional, List
from collections import deque

@dataclass
class Process:
    pid: int
    arrival: int
    burst: int
    remaining: int = 0
    start_time: Optional[int] = None
    finish_time: Optional[int] = None

    def __post_init__(self):
        self.remaining = self.burst

    @property
    def waiting_time(self):
        return self.finish_time - self.arrival - self.burst

    @property
    def turnaround_time(self):
        return self.finish_time - self.arrival

    @property
    def response_time(self):
        return self.start_time - self.arrival


def clone(procs):
    return [Process(p.pid, p.arrival, p.burst) for p in procs]


def metrics(procs):
    awt = sum(p.waiting_time    for p in procs) / len(procs)
    att = sum(p.turnaround_time for p in procs) / len(procs)
    art = sum(p.response_time   for p in procs) / len(procs)
    total = max(p.finish_time   for p in procs)
    tp  = len(procs) / total
    return {"awt": awt, "att": att, "art": art, "tp": tp}

def fifo(procs_in):
    """FIFO"""
    procs = clone(procs_in)
    procs.sort(key=lambda p: p.arrival)
    time = 0
    for p in procs:
        if time < p.arrival:
            time = p.arrival
        p.start_time = time
        time += p.burst
        p.finish_time = time
    return procs

def sjf(procs_in):
    """処理時間順"""
    procs = clone(procs_in)
    not_started = sorted(procs, key=lambda p: p.arrival)
    ready: List[Process] = []
    done = []
    time = 0
    while not_started or ready:
        i = 0
        while i < len(not_started):
            if not_started[i].arrival <= time:
                ready.append(not_started.pop(i))
            else:
                i += 1
        if not ready:
            time = not_started[0].arrival
            continue
        ready.sort(key=lambda p: p.burst)
        p = ready.pop(0)
        p.start_time = time
        time += p.burst
        p.finish_time = time
        done.append(p)
    return done

def mlfq(procs_in, quanta=(4, 8, 16), boost_interval=50):
    """
    多重レベルフィードバック
    - キュー0（最高優先）: quantum=4
    - キュー1           : quantum=8
    - キュー2（最低優先）: quantum=16
    - boost_interval 単位時間ごとに全プロセスをキュー0へ昇格（飢餓防止）
    """
    procs = clone(procs_in)
    not_started = sorted(procs, key=lambda p: p.arrival)
    queues = [deque() for _ in quanta]
    done = []
    time = 0
    last_boost = 0

    def add_arrived():
        nonlocal not_started
        arrived = [p for p in not_started if p.arrival <= time]
        not_started = [p for p in not_started if p.arrival > time]
        for p in sorted(arrived, key=lambda x: x.arrival):
            queues[0].append(p)

    add_arrived()

    while any(queues) or not_started:
        if time - last_boost >= boost_interval:
            for i in range(1, len(queues)):
                while queues[i]:
                    queues[0].append(queues[i].popleft())
            last_boost = time

        level = next((i for i, q in enumerate(queues) if q), None)
        if level is None:
            time = not_started[0].arrival
            add_arrived()
            continue

        p = queues[level].popleft()
        if p.start_time is None:
            p.start_time = time

        quantum = quanta[level]
        run = min(quantum, p.remaining)
        time += run
        p.remaining -= run
        add_arrived()

        if p.remaining == 0:
            p.finish_time = time
            done.append(p)
        else:
            queues[min(level + 1, len(queues) - 1)].append(p)

    return done

def workload_A():
    """CPUバウンド"""
    random.seed(42)
    return [Process(pid=i, arrival=i*2, burst=random.randint(20, 40)) for i in range(8)]

def workload_B():
    """対話型"""
    random.seed(99)
    procs = [Process(pid=i, arrival=i, burst=random.randint(2, 6)) for i in range(8)]
    procs.append(Process(pid=8, arrival=0, burst=50))
    procs.append(Process(pid=9, arrival=1, burst=60))
    return procs

def workload_C():
    """混合"""
    bursts = [3, 5, 35, 2, 40, 4, 30, 6, 2, 35]
    return [Process(pid=i, arrival=i, burst=b) for i, b in enumerate(bursts)]


ALGOS = [
    ("FIFO", fifo),
    ("処理時間順", sjf),
    ("MLFQ", mlfq),
]

WORKLOADS = [
    ("ワークロードA（CPUバウンド）", workload_A),
    ("ワークロードB（対話型）",       workload_B),
    ("ワークロードC（混合）",        workload_C),
]

all_results = {}

for wl_name, wl_fn in WORKLOADS:
    base = wl_fn()
    print(f"\n{'='*60}")
    print(f"  {wl_name}")
    print(f"  プロセス数: {len(base)}, バースト時間: {[p.burst for p in base]}")
    print(f"{'='*60}")
    print(f"  {'アルゴリズム':<20} {'平均待ち':>8} {'ターンAR':>8} {'応答時間':>8} {'スループット':>12}")
    print(f"  {'-'*58}")

    wl_results = {}
    for algo_name, algo_fn in ALGOS:
        r = metrics(algo_fn(base))
        print(f"  {algo_name:<20} {r['awt']:>8.2f} {r['att']:>8.2f} {r['art']:>8.2f} {r['tp']:>12.4f}")
        wl_results[algo_name] = r
    all_results[wl_name] = wl_results


print(f"\n\n{'='*70}")
print("  【横断サマリー】各指標の最小値を ★ で示す")
print(f"{'='*70}")

for metric_key, metric_label in [("awt", "平均待ち時間"), ("art", "平均応答時間")]:
    print(f"\n  ▼ {metric_label}（小さいほど良い）")
    wl_shorts = ["WL-A", "WL-B", "WL-C"]
    print(f"  {'アルゴリズム':<20}", end="")
    for s in wl_shorts:
        print(f"  {s:>8}", end="")
    print()
    print(f"  {'-'*46}")
    for algo_name, _ in ALGOS:
        print(f"  {algo_name:<20}", end="")
        for wl_name, _ in WORKLOADS:
            val = all_results[wl_name][algo_name][metric_key]
            best = min(all_results[wl_name][a][metric_key] for a, _ in ALGOS)
            mark = "★" if abs(val - best) < 0.01 else " "
            print(f"  {val:>6.2f}{mark}", end="")
        print()
