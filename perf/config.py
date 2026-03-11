import json
import os, yaml

def deep_merge(a: dict, b: dict) -> dict:
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
print("CFG: ", json.dumps(CFG, indent=4))
WEIGHTS = CFG["load"]["flow_weights"]
