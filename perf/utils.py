import uuid, time, random, base64
from typing import Dict
from perf.config import CFG

def hdr_with_corr(headers: dict) -> dict:
    h = dict(headers or {})
    h[CFG["observability"]["correlation_header"]] = str(uuid.uuid4())
    return h

def next_refresh_epoch(minutes: int, jitter: int) -> float:
    delta = minutes * 60
    if jitter:
        delta += random.uniform(-jitter*60, jitter*60)
    return time.time() + max(30, delta)

def basic_header(u: str, p: str) -> Dict[str, str]:
    b64 = base64.b64encode(f"{u}:{p}".encode()).decode()
    return {"Authorization": f"Basic {b64}"}

def merge_params(a: dict | None, b: dict | None) -> dict:
    out = dict(a or {}); out.update(b or {}); return out

def join_v2(base: str, path: str) -> str:
    base = base.rstrip("/")
    if "api2" in base and path.startswith("/api/v2"):
        after = path.split("/api2")[-1]
        return base + after
    return base + path

def http_opts():
    opts = {"timeout": CFG["service"].get("timeout_s", 15)}
    # allow a path to a CA bundle OR a boolean
    ca_bundle = CFG["service"].get("ca_bundle")
    if ca_bundle:
        opts["verify"] = ca_bundle
    elif "verify_ssl" in CFG["service"]:
        opts["verify"] = bool(CFG["service"]["verify_ssl"])
    if CFG["service"].get("proxies"):
        opts["proxies"] = CFG["service"]["proxies"]
    return opts

# Optional: silence SSL warnings when verify=false
if CFG["service"].get("verify_ssl") is False and not CFG["service"].get("ca_bundle"):
    import urllib3
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)