# perf/base_user.py
from locust import HttpUser, between
from perf.login_ops import LoginOps
from perf.cred_pool import pop_v1, pop_v2, push_v1, push_v2
from perf.config import CFG
from perf.utils import next_refresh_epoch

class ApiUserBase(LoginOps, HttpUser):
    """
    Subclasses declare which stacks they touch:
    - set USE_V1 = True if they do v1 calls
    - set USE_V2 = True if they do v2 calls
    """
    wait_time = between(0, 0)
    USE_V1 = True
    USE_V2 = True

    def on_start(self):
        self.v1_user_cred = None
        self.v2_user_cred = None

        if self.USE_V1:
            self.v1_user_cred = pop_v1()
            u, p = self.v1_user_cred
            self._login_v1(u, p)

        if self.USE_V2:
            self.v2_user_cred = pop_v2()
            u, p = self.v2_user_cred
            self._login_v2(u, p)

        rt = CFG["load"]["refresh_token"]
        self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))

    def on_stop(self):
        push_v1(getattr(self, "v1_user_cred", None))
        push_v2(getattr(self, "v2_user_cred", None))

    def maybe_refresh_tokens(self):
        import time
        if time.time() < getattr(self, "next_refresh_at", 0):
            return
        # optional logout(s)
        if CFG["load"]["refresh_token"].get("logout_on_refresh", True):
            self._logout_if_configured()
        # re-login with the SAME pool-specific creds
        if self.USE_V1 and self.v1_user_cred:
            u, p = self.v1_user_cred
            self._login_v1(u, p)
        if self.USE_V2 and self.v2_user_cred:
            u, p = self.v2_user_cred
            self._login_v2(u, p)

        rt = CFG["load"]["refresh_token"]
        self.next_refresh_at = next_refresh_epoch(rt["by_time_minutes"], rt.get("jitter_minutes", 0))
