import math
import os
import random, time
import uuid

import yaml
from faker import Faker
fake = Faker()

def think(min_ms: int, max_ms: int):
    time.sleep(random.uniform(min_ms, max_ms)/1000)

def random_emp_body():
    return {"name": fake.name(), "dept": random.choice(["ENG","HR","FIN"])}


def deep_merge(a: dict, b: dict):
    r = dict(a or {})
    for k, v in (b or {}).items():
        if k in r and isinstance(r[k], dict) and isinstance(v, dict):
            r[k] = deep_merge(r[k], v)
        else:
            r[k] = v
    return r


def load_cfg():
    env = os.getenv("ENV", "dev")
    with open("config/base.yaml", "r") as f:
        base = yaml.safe_load(f) or {}
    envfile = f"config/{env}.yaml"
    if os.path.exists(envfile):
        with open(envfile, "r") as f:
            envd = yaml.safe_load(f) or {}
        base = deep_merge(base, envd)
    return base


CFG = load_cfg()
WEIGHTS = CFG["load"]["flow_weights"]


def get_json_path(data, path: str, default=None):
    if not isinstance(data, dict):
        return default
    cur = data
    for part in (path or "").split("."):
        if part == "":
            continue
        if not isinstance(cur, dict):
            return default
        cur = cur.get(part, default)
    return cur


def auth_body(username, password):
    return {"username": username, "password": password}


def next_refresh_epoch(minutes: int, jitter: int) -> float:
    delta = minutes * 60
    if jitter:
        delta += random.uniform(-jitter*60, jitter*60)
    return time.time() + max(30, delta)


def employees_total_pages():
    pag = CFG["operations"]["employees"]["list_pagination"]
    total = int(pag.get("total_count", 0))
    page_size = int(pag.get("page_size", 2000))
    if page_size <= 0: page_size = 2000
    return max(1, math.ceil(total / page_size))


def employees_page_params(page_index: int):
    pag = CFG["operations"]["employees"]["list_pagination"]
    mode = pag.get("mode", "page_size")
    if mode == "offset_limit":
        limit = int(pag.get("page_size", 2000))
        offset = page_index * limit
        return { pag.get("offset_param","offset"): offset, pag.get("limit_param","limit"): limit }
    else:
        page_param = pag.get("page_param","page")
        size_param = pag.get("size_param","size")
        one_based = bool(pag.get("page_one_based", False))
        page_num = page_index + 1 if one_based else page_index
        return { page_param: page_num, size_param: int(pag.get("page_size",2000)) }


def hdr_with_corr(headers: dict) -> dict:
    h = dict(headers)
    h[CFG["observability"]["correlation_header"]] = str(uuid.uuid4())
    return h
