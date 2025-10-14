# perf/cred_pool.py
import csv, os
from gevent.queue import Queue, Empty
from locust import events
from locust.exception import StopUser
from perf.config import CFG

CRED_V1 = Queue()
CRED_V2 = Queue()

def _load_csv(path):
    with open(path) as f:
        return [(r[0], r[1]) for r in csv.reader(f) if r and len(r) >= 2]

@events.test_start.add_listener
def seed_creds(environment, **_):
    # clear queues
    for q in (CRED_V1, CRED_V2):
        while not q.empty():
            try: q.get_nowait()
            except Empty: break

    v1_path = CFG["auth"].get("v1_users_csv") or CFG["auth"]["users_csv"]
    v2_path = CFG["auth"].get("v2_users_csv") or CFG["auth"]["users_csv"]

    if v1_path == v2_path:
        # single file → split rows into two disjoint sets (even/odd)
        rows = _load_csv(v1_path)
        for i, row in enumerate(rows):
            (CRED_V1 if i % 2 == 0 else CRED_V2).put(row)
    else:
        for row in _load_csv(v1_path): CRED_V1.put(row)
        for row in _load_csv(v2_path): CRED_V2.put(row)

    print(f"[cred_pool] V1={CRED_V1.qsize()} V2={CRED_V2.qsize()} "
          f"(v1_csv={v1_path}, v2_csv={v2_path})")

def pop_v1():
    try: return CRED_V1.get_nowait()
    except Empty: raise StopUser("No free V1 credentials")

def pop_v2():
    try: return CRED_V2.get_nowait()
    except Empty: raise StopUser("No free V2 credentials")

def push_v1(cred):
    if cred: CRED_V1.put(cred)

def push_v2(cred):
    if cred: CRED_V2.put(cred)
