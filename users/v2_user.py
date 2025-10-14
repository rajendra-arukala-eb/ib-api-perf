import datetime
import math

from locust import task, tag
import random, uuid
from typing import List
from perf.base_user import ApiUserBase
from perf.config import CFG, WEIGHTS
from perf.utils import hdr_with_corr, join_v2, http_opts
import datetime as dt

def employees_total_pages():
    pag = CFG["operations"]["employees"]["list_pagination"]
    total = int(pag.get("total_count", 0))
    page_size = int(pag.get("page_size", 2000))
    if page_size <= 0: page_size = 2000
    return max(1, math.ceil(total / page_size))


@tag("v2")
class V2WritesUser(ApiUserBase):
    """v2 write operations (create/update/delete, users list)."""
    USE_V1 = False
    USE_V2 = True
    def on_start(self):
        super().on_start()
        self.page_cursor = random.randint(0, employees_total_pages()-1)
        self.recent_ids: List[int] = []
        self.recent_emps = []

    @tag("v2","v2_list_employees")
    @task(weight=WEIGHTS.get("v2_list_employees", 0))
    def v2_list_employees(self):
        self.maybe_refresh_tokens()
        url = join_v2(self.v2_base, CFG["operations"]["employees2"]["list_path"])
        self.page_cursor = (self.page_cursor + 1) % employees_total_pages()
        pag = CFG["operations"]["employees2"]["list_pagination"] or {}
        params = dict(self.v2_query or {})
        params['start'] = self.page_cursor
        params['take'] = pag.get("page_size", 2000)

        with self.client.get(url, params=params, headers=hdr_with_corr(self.v2_headers), name="v2_list_employees", **http_opts(), catch_response=True) as r:
            if r.status_code == 401:
                u, p = self.user_cred; self._login_v2(u, p)
                r.failure("Unauthorized - re-logged in")
            elif r.status_code != 200:
                print("Failure: ", r.text)
                r.failure(f"Unexpected status code: {r.status_code}")
            else:
                try:
                    data = r.json() or {}
                    items = data.get("results") if isinstance(data, dict) else []
                    if isinstance(items, list):
                        for item in items:
                            emp_id = item.get("id")
                            if emp_id and emp_id not in self.recent_ids:
                                self.recent_ids.append(emp_id)
                    r.success()
                except Exception as e:
                    r.failure(f"Failed to parse JSON response: {e}")
        self.think()

    @tag("v2","v2_get_employee")
    @task(weight=WEIGHTS.get("v2_get_employee", 0))
    def v2_get_employee(self):
        self.maybe_refresh_tokens()
        path_tpl = CFG["operations"]["employees2"]["get_path"]
        seeded = CFG["operations"]["employees2"]["seeded"]["emp_ids"] or []
        emp_id = random.choice(self.recent_ids) if self.recent_ids else random.choice(seeded)

        url = join_v2(self.v2_base, path_tpl.format(id=emp_id))
        params = dict(self.v2_query or {})
        print("URL: ", url, " PARAMS: ", params)

        with self.client.get(url, params=params, headers=hdr_with_corr(self.v2_headers), name="v2_get_employee", **http_opts(), catch_response=True) as r:
            if r.status_code == 401:
                u, p = self.user_cred; self._login_v2(u, p)
                r.failure("Unauthorized - re-logged in")
            elif r.status_code != 200:
                r.failure(f"Unexpected status code: {r.status_code}")
            else:
                try:
                    data = r.json() or {}
                    print("DATA: ", data)
                    print("RECENT EMP: ", len(self.recent_emps))
                    if data.get("results") and isinstance(data.get("results"), list ) and len(data.get("results"))>0:
                        self.recent_emps.append(data.get("results")[0])
                    if len(self.recent_emps) > 100:
                        self.recent_emps = self.recent_emps[-50:]
                    r.success()
                except Exception as e:
                    r.failure(f"Failed to parse JSON response: {e}")
        self.think()



    @tag("v2","v2_update_employee")
    @task(weight=WEIGHTS.get("v2_update_employee", 0))
    def v2_update_employee(self):
        self.maybe_refresh_tokens()
        path_tpl = CFG["operations"]["employees2"]["get_path"]
        seeded = CFG["operations"]["employees2"]["seeded"]["emp_ids"] or []
        emp = random.choice(self.recent_emps) if self.recent_emps else {}
        emp_id = emp.get("id")

        url = join_v2(self.v2_base, path_tpl.format(id=emp_id))
        params = dict(self.v2_query or {})
        ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
        body = {"lastName": emp.get("lastName", "") + f" UPDATED-{ts}"}
        print("URL: ", url, " PARAMS: ", params, " BODY: ", body)

        if emp:
            with self.client.put(url, params=params, json= body, headers=hdr_with_corr(self.v2_headers), name="v2_update_employee", **http_opts(), catch_response=True) as r:
                print("RESPONSE: ", r.status_code, r.text)
                if r.status_code == 401:
                    u, p = self.user_cred; self._login_v2(u, p)
                    r.failure("Unauthorized - re-logged in")
                elif r.status_code != 200:
                    r.failure(f"Unexpected status code: {r.status_code}")
                else:
                    try:
                        data = r.json() or {}
                        print(data)
                        r.success()
                    except Exception as e:
                        r.failure(f"Failed to parse JSON response: {e}")
            self.think()

    # @tag("v2","get_all_users")
    # @task(weight=WEIGHTS.get("get_all_users", 0))
    # def get_all_users(self):
    #     self.maybe_refresh_tokens()
    #     url = join_v2(self.v2_base, CFG["operations"]["users"]["get_all_path"])
    #     r = self.client.get(url, params=self.v2_query, headers=hdr_with_corr(self.v2_headers), name="get_all_users", **http_opts())
    #     if r.status_code == 401:
    #         u, p = self.user_cred; self._login_v2(u, p)
    #     self.think()
