from typing import Optional
from locust import events
from perf.config import CFG
from perf.utils import basic_header, next_refresh_epoch, http_opts


class LoginOps:
    """Shared login/refresh/logout for v1/v2. Meant as a mixin with HttpUser."""

    def _ensure_auth_containers(self):
        if not hasattr(self, "v1_headers"): self.v1_headers = {"Accept": "application/json"}
        if not hasattr(self, "v1_query"):   self.v1_query   = {}
        if not hasattr(self, "v2_headers"): self.v2_headers = {"Accept": "application/json", "Content-Type": "application/json"}
        if not hasattr(self, "v2_query"):   self.v2_query   = {}
        if not hasattr(self, "v2_base"):    self.v2_base    = CFG["service"]["rest_v2_base_url"].rstrip("/")

    def login_both(self, username: str, password: str):
        self._login_v1(username, password)
        self._login_v2(username, password)
        rt = CFG["load"]["refresh_token"]
        self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))

    # ----- v1 -----
    def _login_v1(self, username: str, password: str):
        self._ensure_auth_containers()
        base = CFG["service"]["rest_v1_base_url"].rstrip("/")
        url  = base + CFG["auth"].get("v1_login_path", "/rest/api/login") + "?output=json"

        names = CFG["auth"].get("v1_header_names", {})
        hdrs = {
            "Accept": "application/json",
            names.get("login","loginName"): username,
            names.get("password","password"): password,
        }
        cust_id = CFG["auth"].get("custId")
        if cust_id:
            hdrs[names.get("custId","custId")] = str(cust_id)

        #print(f"[auth] v1 login attempt for user '{username}' at {url}")
        with self.client.post(url, headers=hdrs, name="(auth) v1_login", catch_response=True, **http_opts()) as r:
            if r.status_code != 200:
                #print(f"[auth] v1 login failed for user '{username}' and headers '{hdrs}' with status {r.status_code}")
                r.failure(f"v1 login failed {r.status_code}")
                return
            try:
                data = r.json() or {}
                #print("Received: ", data)
            except Exception:
                r.failure("v1 login: expected JSON; ensure ?output=json")
                return
            sid = data.get("sessionId")
            if not sid:
                r.failure("v1 login: sessionId missing")
                return

            mode = CFG["auth"]["v1_session_propagation"]["mode"]
            name = CFG["auth"]["v1_session_propagation"]["name"]
            if mode == "header":
                self.v1_headers[name] = sid
            elif mode == "query":
                self.v1_query[name] = sid
            # cookie mode: rely on Set-Cookie
            r.success()

    # ----- v2 -----
    def _login_v2(self, username: str, password: str):
        self._ensure_auth_containers()
        login_path = CFG["auth"].get("v2_login_path", "/rest/api2/login")
        login_url  = CFG["service"]["rest_v2_base_url"].rstrip("/") + login_path

        use_basic = CFG["auth"].get("v2_login_basic", True)
        headers = basic_header(username, password) if use_basic else {}
        body    = None if use_basic else {"username": username, "password": password}

        # print(f"[auth] v2 login attempt for user '{username}' at {login_url} using {'basic' if use_basic else 'json body'}")
        with self.client.post(login_url, headers=headers, json=body, name="(auth) v2_login", **http_opts(), catch_response=True) as r:
            if r.status_code != 200:
                r.failure(f"v2 login failed {r.status_code}")
                return
            data = {}
            try:
                data = r.json() or {}
                # Some deployments wrap in {"results":[{...}]}
                if isinstance(data, dict) and "results" in data and isinstance(data["results"], list) and data["results"]:
                    data = data["results"][0]
            except Exception:
                pass

            # adopt server-provided base url if present
            if isinstance(data.get("JWT"), str) and data["JWT"]:
                self.v2_headers['JWT'] = data['JWT']

            # adopt server-provided base url if present
            if isinstance(data.get("url"), str) and data["url"]:
                self.v2_base = data["url"].rstrip("/")

            r.success()

    def _logout_if_configured(self):
        if CFG["load"]["refresh_token"].get("logout_on_refresh", True):
            v1p = CFG["auth"].get("v1_login_path","/rest/api/login").replace("login","logout")
            url1 = CFG["service"]["rest_v1_base_url"].rstrip("/") + v1p
            self.client.post(url1, headers=self.v1_headers, params=self.v1_query, name="(auth) v1_logout", **http_opts())

            v2p = CFG["auth"].get("v2_login_path","/rest/api2/login").replace("login","logout")
            if "/api2" in self.v2_base:
                url2 = self.v2_base + v2p.split("/api2")[-1]
            else:
                url2 = CFG["service"]["rest_v2_base_url"].rstrip("/") + v2p
            self.client.post(url2, headers=self.v2_headers, params=self.v2_query, name="(auth) v2_logout", **http_opts())

    def maybe_refresh_tokens(self):
        import time
        if not hasattr(self, "next_refresh_at"):
            return
        if time.time() >= self.next_refresh_at:
            self._logout_if_configured()
            u, p = self.user_cred
            self._login_v1(u, p)
            self._login_v2(u, p)
            rt = CFG["load"]["refresh_token"]
            self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))

    def think(self):
        a, b = CFG["load"]["think_time_range_ms"]
        import time, random
        time.sleep(random.uniform(a, b)/1000)
