import json
from typing import Optional

import requests

from customers.config import LOGIN_URL
from customers.login import get_jwt


def get_headers(jwt):
    return { "Content-Type": "application/json", "JWT": jwt }

def install_application_xml(
        base_url: str,
        jwt: str,
        xml_content: str,
        override_changes: bool = True,
        override_permissions: bool = False,
        ignore_warnings: bool = False,
        accept_version: str | None = None,   # e.g. "6.6.0.0" if needed
        timeout: int = 120
):
    url = f"{base_url}meta/applications"  # change path if your spec uses a different one

    params = {
        "overrideChanges": str(override_changes).lower(),
        "overridePermissions": str(override_permissions).lower(),
        "ignoreWarnings": str(ignore_warnings).lower(),
    }

    headers = {
        "Content-Type": "application/xml",
        "JWT": jwt,
    }
    if accept_version:
        headers["Accept-Version"] = accept_version

    resp = requests.post(url, params=params, data=xml_content.encode("utf-8"), headers=headers, timeout=timeout)

    if resp.status_code not in (200, 201, 202):
        raise Exception(f"Install failed: {resp.status_code} - {resp.text}")

    # Some installs return JSON, some return text; keep it flexible.
    try:
        return resp.json()
    except Exception:
        return resp.text


def import_csv(
        base_url: str,
        jwt: str,
        csv_content: str | bytes,
        map_integration_name: str,
        field_integration_name: Optional[str] = None,
        trigger_integration_name: Optional[str] = None,
        synch: bool = False,
        import_type: int = 0,
        import_mode: int = 0,
        create_action: bool = False,
        treat_empty_cell_as_null: bool = False,
        timeout: int = 300,
):
    """
    Executes POST /data/import with text/csv payload
    """

    url = f"{base_url}data/import"

    params = {
        "mapIntegrationName": map_integration_name,
        "synch": str(synch).lower(),
        "importType": import_type,
        "importMode": import_mode,
        "createAction": str(create_action).lower(),
        "treatEmptyCellAsNull": str(treat_empty_cell_as_null).lower(),
    }

    # Optional params
    if field_integration_name:
        params["fieldIntegrationName"] = field_integration_name
    if trigger_integration_name:
        params["triggerIntegrationName"] = trigger_integration_name

    headers = {
        "Content-Type": "text/csv",
        "JWT": jwt,
    }

    # requests accepts both str and bytes
    data = csv_content.encode("utf-8") if isinstance(csv_content, str) else csv_content

    print("Importing CSV with params:", params)
    print("URL:", url)
    print("Headers:", headers)
    resp = requests.post(
        url,
        params=params,
        data=data,
        headers=headers,
        timeout=timeout,
    )

    if resp.status_code not in (200, 201, 202):
        raise Exception(f"Bulk upload failed: {resp.status_code} - {resp.text}")

    # sync=true usually returns JSON with IDs
    # async may return plain text or job info
    try:
        return resp.json()
    except Exception:
        return resp.text

if __name__ == "__main__":
    with open("cust-user-data.json", "r") as data_file:
        data = json.load(data_file)
        for item in data:
            username = item.get("loginName")
            password = "welcome"
            cust_id = item.get("custId")
            print(f"Getting JWT for user: {username} (Customer ID: {cust_id})")
            jwt, api_url = get_jwt(username, password, LOGIN_URL)

            with open("resources/ViewsRecordsAndFiltersAutomationApp_v137", "r") as xml_file:
                xml_content = xml_file.read()
                install_application_xml(api_url, jwt, xml_content)
            # with open("resources/automation-object-records.csv", "r") as csv_file:
            #     csv_content = csv_file.read()
            #     import_csv(api_url, jwt, csv_content, "all_columns")