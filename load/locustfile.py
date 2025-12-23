from locust import HttpUser, task, between, events, tag
import csv, random, time, uuid, math, os, base64
from typing import Optional
import yaml
from load.ops import build_list_params, build_update_body, build_create_body
from perf.utils import http_opts

from users.v1_user import V1ReadsUser
from users.v2_user import V2WritesUser


# -------- Config loading --------
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

# -------- Helpers --------
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

def hdr_with_corr(headers: dict) -> dict:
    h = dict(headers or {})
    h[CFG["observability"]["correlation_header"]] = str(uuid.uuid4())
    return h

def _basic_header(u: str, p: str) -> dict:
    b64 = base64.b64encode(f"{u}:{p}".encode()).decode()
    return {"Authorization": f"Basic {b64}"}

def _merge_params(a: dict | None, b: dict | None) -> dict:
    out = dict(a or {}); out.update(b or {}); return out

# -------- User with v1 session + v2 JWT --------
class V1V2ApiUser(HttpUser):
    """
    - v1 (REST 1.0): login via headers -> sessionId -> header/query/cookie on reads
    - v2 (REST 2.0): login via Basic -> JWT -> Authorization header on writes
    - v2 "url" from login response overrides rest_v2_base_url
    """
    wait_time = between(0, 0)

    def on_start(self):
        with open(CFG["auth"]["users_csv"]) as f:
            rows = list(csv.reader(f))
        if not rows:
            raise RuntimeError("No users in CSV")
        self.user_cred = random.choice(rows)

        # v1 state
        self.v1_session_id: Optional[str] = None
        self.v1_headers = {"Accept": "application/json"}
        self.v1_query = {}

        # v2 state
        self.v2_headers = {"Accept": "application/json"}
        self.v2_query = {}
        self.v2_base = CFG["service"]["rest_v2_base_url"].rstrip("/")

        # pagination + id cache
        self.page_cursor = random.randint(0, employees_total_pages()-1)
        self.recent_ids: list[int] = []

        self._login_v1()
        self._login_v2()
        rt = CFG["load"]["refresh_token"]
        self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))

    # ----- v1 login -----
    def _login_v1(self):
        u, p = self.user_cred
        base = CFG["service"]["rest_v1_base_url"].rstrip("/")
        url = base + CFG["auth"].get("v1_login_path", "/rest/api/login") + "?output=json"

        names = CFG["auth"].get("v1_header_names", {})
        hdrs = {
            "Accept": "application/json",
            names.get("login","loginName"): u,
            names.get("password","password"): p,
        }
        cust_id = CFG["auth"].get("custId")
        if cust_id:
            hdrs[names.get("custId","custId")] = str(cust_id)

        with self.client.post(url, headers=hdrs, name="(auth) v1_login", catch_response=True , **http_opts()) as r:
            if r.status_code != 200:
                r.failure(f"v1 login failed {r.status_code}")
                return
            try:
                data = r.json()
                print("V1 login response:", data)
            except Exception:
                r.failure("v1 login: expected JSON; ensure ?output=json")
                return
            sid = data.get("sessionId")
            if not sid:
                r.failure("v1 login: sessionId missing")
                return

            self.v1_session_id = sid
            mode = CFG["auth"]["v1_session_propagation"]["mode"]
            name = CFG["auth"]["v1_session_propagation"]["name"]
            if mode == "header":
                self.v1_headers[name] = sid
            elif mode == "query":
                self.v1_query[name] = sid
            # cookie mode: rely on Set-Cookie
            r.success()

    # ----- v2 login -----
    def _login_v2(self):
        u, p = self.user_cred
        login_url = CFG["service"]["rest_v2_base_url"].rstrip("/") + CFG["auth"].get("v2_login_path", "/rest/api2/login")

        if CFG["auth"].get("v2_login_basic", True):
            hdrs = _basic_header(u, p)
            body = None
        else:
            hdrs = {}
            body = {"username": u, "password": p}

        with self.client.post(login_url, headers=hdrs, json=body, name="(auth) v2_login", catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"v2 login failed {r.status_code}")
                return
            data = {}
            try:
                data = r.json() or {}
                data = data['results'][0]
                print("V2 login response:", data)
            except Exception:
                pass

            token = data.get(CFG["auth"].get("v2_token_json_path", "JWT"))
            if not token and CFG["auth"].get("v2_token_fallback_header"):
                token = r.headers.get(CFG["auth"]["v2_token_fallback_header"])
            if not token:
                r.failure("v2 login: token missing")
                return

            # hdr = CFG["auth"].get("v2_token_header", "Authorization")
            # scheme = CFG["auth"].get("v2_token_scheme", "Bearer")
            # self.v2_headers[hdr] = f"{scheme} {token}"
            self.v2_headers['JWT'] = token

            print("V2 JWT token acquired:", self.v2_headers)

            # adopt server-provided base url if present
            if isinstance(data.get("url"), str) and data["url"]:
                self.v2_base = data["url"].rstrip("/")

            print("V2 base URL:", self.v2_base)

            # # ensure integration name is attached
            # integ = CFG["auth"].get("v2_integration", {})
            # name = integ.get("name","integrationName")
            # value = integ.get("value","ib-perf-harness")
            # if integ.get("mode","query") == "query":
            #     self.v2_query[name] = value
            # else:
            #     self.v2_headers[name] = value
            r.success()

    def _logout_if_configured(self):
        if CFG["load"]["refresh_token"].get("logout_on_refresh", True):
            # v1 logout (best-effort; endpoint derived from login path)
            v1p = CFG["auth"].get("v1_login_path","/rest/api/login").replace("login","logout")
            url1 = CFG["service"]["rest_v1_base_url"].rstrip("/") + v1p
            self.client.post(url1, headers=self.v1_headers, params=self.v1_query, name="(auth) v1_logout")

            # v2 logout (best-effort; derived similarly)
            v2p = CFG["auth"].get("v2_login_path","/rest/api2/login").replace("login","logout")
            # If v2_base contains /prodN/api2 already, avoid duplicating /rest/api2
            if "/api2" in self.v2_base:
                url2 = self.v2_base + v2p.split("/api2")[-1]
            else:
                url2 = CFG["service"]["rest_v2_base_url"].rstrip("/") + v2p
            self.client.post(url2, headers=self.v2_headers, params=self.v2_query, name="(auth) v2_logout")

    def _maybe_refresh_tokens(self):
        if time.time() >= self.next_refresh_at:
            self._logout_if_configured()
            self._login_v1()
            self._login_v2()
            rt = CFG["load"]["refresh_token"]
            self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))

    def _think(self):
        a, b = CFG["load"]["think_time_range_ms"]
        time.sleep(random.uniform(a, b)/1000)

    # ----- Tasks -----
    @tag("list_employees")
    @task(weight=WEIGHTS.get("list_employees", 0))
    def list_employees(self):
        self._maybe_refresh_tokens()
        url = CFG["service"]["rest_v1_base_url"].rstrip("/") + CFG["operations"]["employees"]["list_path"]
        pag = CFG["operations"]["employees"]["list_pagination"]
        params = _merge_params(self.v1_query, build_list_params(pag, self.page_cursor))
        with self.client.get(url, params=params, headers=hdr_with_corr(self.v1_headers), name="employees_list", catch_response=True) as r:
            if r.status_code in (200, 206):
                try:
                    data = r.json()
                    items = data.get("items") if isinstance(data, dict) else data
                    if isinstance(items, list):
                        for it in items[:50]:
                            if isinstance(it, dict):
                                emp_id = it.get("id")
                                if emp_id:
                                    self.recent_ids.append(emp_id)
                        if len(self.recent_ids) > 3000:
                            self.recent_ids = self.recent_ids[-1500:]
                except Exception:
                    pass
                r.success()
            else:
                if r.status_code == 401:
                    self._login_v1()
                r.failure(f"employees_list {r.status_code}")
        self.page_cursor = (self.page_cursor + 1) % employees_total_pages()
        self._think()

    @tag("list_locations")
    @task(weight=WEIGHTS.get("list_locations", 0))
    def list_locations(self):
        self._maybe_refresh_tokens()
        url = CFG["service"]["rest_v1_base_url"].rstrip("/") + CFG["operations"]["locations"]["list_path"]
        r = self.client.get(url, params=self.v1_query, headers=hdr_with_corr(self.v1_headers), name="locations_list")
        if r.status_code == 401:
            self._login_v1()
        self._think()

    @tag("create_employee")
    @task(weight=WEIGHTS.get("create_employee", 0))
    def create_employee(self):
        self._maybe_refresh_tokens()
        url = self.v2_base + CFG["operations"]["employees"]["create_path"]
        body = build_create_body(f"User{uuid.uuid4()}", random.choice(["ENG","HR","FIN"]))
        r = self.client.post(url, params=self.v2_query, json=body, headers=hdr_with_corr(self.v2_headers), name="employees_create")
        if r.status_code == 401:
            self._login_v2()
        else:
            try:
                emp_id = (r.json() or {}).get("id")
                if emp_id:
                    self.recent_ids.append(emp_id)
            except Exception:
                pass
        self._think()

    @tag("update_employee")
    @task(weight=WEIGHTS.get("update_employee", 0))
    def update_employee(self):
        self._maybe_refresh_tokens()
        emp_id = random.choice(self.recent_ids) if self.recent_ids else random.randint(1, int(CFG["operations"]["employees"]["list_pagination"].get("total_count", 1000)))
        path_tpl = CFG["operations"]["employees"]["update_path"]
        url = self.v2_base + path_tpl.format(id=emp_id)
        body = build_update_body(random.randint(1,10))
        r = self.client.put(url, params=self.v2_query, json=body, headers=hdr_with_corr(self.v2_headers), name="employees_update")
        if r.status_code == 401:
            self._login_v2()
        self._think()

    @tag("delete_employee")
    @task(weight=WEIGHTS.get("delete_employee", 0))
    def delete_employee(self):
        self._maybe_refresh_tokens()
        emp_id = self.recent_ids.pop(0) if self.recent_ids else random.randint(1, int(CFG["operations"]["employees"]["list_pagination"].get("total_count", 1000)))
        path_tpl = CFG["operations"]["employees"]["delete_path"]
        url = self.v2_base + path_tpl.format(id=emp_id)
        r = self.client.delete(url, params=self.v2_query, headers=hdr_with_corr(self.v2_headers), name="employees_delete")
        if r.status_code == 401:
            self._login_v2()
        self._think()

    @tag("get_all_users")
    @task(weight=WEIGHTS.get("get_all_users", 0))
    def get_all_users(self):
        self._maybe_refresh_tokens()
        url = self.v2_base + CFG["operations"]["users"]["get_all_path"]
        print("Getting all users from", url)
        print("Headers: ", self.v2_headers)
        r = self.client.get(url, params=self.v2_query, headers=hdr_with_corr(self.v2_headers), name="get_all_users")
        if r.status_code == 401:
            self._login_v2()
        self._think()



@events.init.add_listener
def _(environment, **kwargs):
    if not environment.host:
        environment.host = CFG["service"]["rest_v1_base_url"]
