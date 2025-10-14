import json

from locust import task, tag
import math, random
from typing import List
from perf.base_user import ApiUserBase
from perf.config import CFG, WEIGHTS
from perf.utils import hdr_with_corr, merge_params, http_opts
from load.ops import build_list_params

def employees_total_pages():
    pag = CFG["operations"]["employees"]["list_pagination"]
    total = int(pag.get("total_count", 0))
    page_size = int(pag.get("page_size", 2000))
    if page_size <= 0: page_size = 2000
    return max(1, math.ceil(total / page_size))

def locations_total_pages():
    pag = CFG["operations"]["locations"]["list_pagination"]
    total = int(pag.get("total_count", 0))
    page_size = int(pag.get("page_size", 200))
    if page_size <= 0: page_size = 200
    return max(1, math.ceil(total / page_size))

def teams_total_pages():
    pag = CFG["operations"]["locations"]["list_pagination"]
    total = int(pag.get("total_count", 0))
    page_size = int(pag.get("page_size", 200))
    if page_size <= 0: page_size = 200
    return max(1, math.ceil(total / page_size))

@tag("v1")
class V1ReadsUser(ApiUserBase):
    """v1-only read operations (list employees/locations)."""
    USE_V1 = True
    USE_V2 = False
    def on_start(self):
        super().on_start()
        self.page_cursor = random.randint(0, employees_total_pages()-1)
        self.page_cursor_loc = random.randint(0, locations_total_pages()-1)
        self.page_cursor_team = random.randint(0, teams_total_pages()-1)
        self.recent_ids: List[int] = []

    @tag("v1","v1_list_employees")
    @task(weight=WEIGHTS.get("v1_list_employees", 0))
    def v1_list_employees(self):
        self.maybe_refresh_tokens()
        url = CFG["service"]["rest_v1_base_url"].rstrip("/") + CFG["operations"]["employees"]["list_path"]
        pag = CFG["operations"]["employees"]["list_pagination"]
        params = merge_params(self.v1_query, build_list_params(pag, self.page_cursor))


        """
        Example:
        https://app.bcinthecloud.com/rest/api/getPage
        ?viewId=17854
        &fieldList=id,firstName,lastName,middleName,employee_id,title,Job_COde,phone,personal_email_address,mobilePhone,home_phone_number,email,Personal_Mobile_Phone,process,Employee_Status,Ppeople,R113586,R50496,R113951,sp_department,sp_location,sp_role,Work_Phone_2
        &rowsPerPage=2000
        &startRow=0
        &output=json
        &sessionId=sessionId
        """
        params["viewId"] = "17854"
        params["fieldList"] = "id,firstName,lastName,middleName,employee_id,title,Job_COde,phone,personal_email_address,mobilePhone,home_phone_number,email,Personal_Mobile_Phone,process,Employee_Status,Ppeople,R113586,R50496,R113951,sp_department,sp_location,sp_role,Work_Phone_2"
        params["rowsPerPage"] = params.get("size", 2000)
        params["startRow"] = (params["page"]) * params["rowsPerPage"] if "page" in params and "rowsPerPage" in params else 0
        params["output"] = "json"
        params["sessionId"] = self.v1_headers.get("sessionId", "")

        with self.client.get(url, params=params, headers=hdr_with_corr(self.v1_headers), name="v1_list_employees", catch_response=True, **http_opts()) as r:
            if r.status_code in (200, 206):
                try:
                    data = r.json()
                    items = data.get("items") if isinstance(data, dict) else data
                    if isinstance(items, list):
                        for it in items[:50]:
                            if isinstance(it, dict):
                                emp_id = it.get("id")
                                if emp_id: self.recent_ids.append(emp_id)
                        if len(self.recent_ids) > 3000:
                            self.recent_ids = self.recent_ids[-1500:]
                except Exception:
                    pass
                r.success()
            else:
                if r.status_code == 401:
                    u, p = self.user_cred; self._login_v1(u, p)

                print("Failure: ", r.json(), " CRED: ", self.user_cred)
                r.failure(f"v1_list_employees {r.status_code}")
        self.page_cursor = (self.page_cursor + 1) % employees_total_pages()
        self.think()

    @tag("v1","v1_list_locations")
    @task(weight=WEIGHTS.get("v1_list_locations", 0))
    def v1_list_locations(self):
        self.maybe_refresh_tokens()
        url = CFG["service"]["rest_v1_base_url"].rstrip("/") + CFG["operations"]["locations"]["list_path"]
        pag = CFG["operations"]["locations"]["list_pagination"]
        params = merge_params(self.v1_query, build_list_params(pag, self.page_cursor_loc))

        """
        Example:
        https://app.bcinthecloud.com/rest/api/getPage
        ?viewId=113473
        &fieldList=id,location_id,name,zip,full_address,country,city,Location_Type
        &rowsPerPage=200
        &startRow=0
        &output=json
        &sessionId=sessionId
        """

        params["viewId"] = "113473"
        params["fieldList"] = "id,location_id,name,zip,full_address,country,city,Location_Type"
        params["rowsPerPage"] = pag.get("page_size", 200)
        params["startRow"] = (self.page_cursor_loc) * params["rowsPerPage"] if "rowsPerPage" in params else 0
        params["output"] = "json"
        params["sessionId"] = self.v1_headers.get("sessionId", "")

        with self.client.get(url, params=params, headers=hdr_with_corr(self.v1_headers), name="v1_list_locations", catch_response=True, **http_opts()) as r:
            if r.status_code == 401:
                u, p = self.user_cred; self._login_v1(u, p)
            else:
                if r.status_code == 200:
                    r.success()
                else:
                    print("Failure: ", r.json(), " CRED: ", self.user_cred)
                    r.failure(f"v1_list_locations {r.status_code}")
        self.page_cursor_loc = (self.page_cursor_loc + 1) % locations_total_pages()
        self.think()

    @tag("v1","v1_list_teams")
    @task(weight=WEIGHTS.get("v1_list_teams", 0))
    def v1_list_teams(self):
        self.maybe_refresh_tokens()
        url = CFG["service"]["rest_v1_base_url"].rstrip("/") + CFG["operations"]["teams"]["list_path"]
        pag = CFG["operations"]["teams"]["list_pagination"]
        params = merge_params(self.v1_query, build_list_params(pag, self.page_cursor_team))

        """
        Example:
        https://app.bcinthecloud.com/rest/api/getPage
        ?viewId=50467
        &fieldList=name,id,team_description,team_type
        &rowsPerPage=200
        &startRow=0
        &output=json
        &sessionId=sessionId
        """

        params["viewId"] = "50467"
        params["fieldList"] = "name,id,team_description,team_type"
        params["rowsPerPage"] = pag.get("page_size", 200)
        params["startRow"] = (self.page_cursor_team) * params["rowsPerPage"] if "rowsPerPage" in params else 0
        params["output"] = "json"
        params["sessionId"] = self.v1_headers.get("sessionId", "")

        with self.client.get(url, params=params, headers=hdr_with_corr(self.v1_headers), name="v1_list_teams", catch_response=True, **http_opts()) as r:
            if r.status_code == 401:
                u, p = self.user_cred; self._login_v1(u, p)
            else:
                if r.status_code == 200:
                    r.success()
                else:
                    print("Failure: ", r.json(), " CRED: ", self.user_cred)
                    r.failure(f"v1_list_teams {r.status_code}")
        self.page_cursor_team = (self.page_cursor_team + 1) % teams_total_pages()
        self.think()
