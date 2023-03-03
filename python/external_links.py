#!/usr/bin/env python3

import json
import os
from urllib.parse import urljoin, urlencode

import pyarrow
import requests

# NOTE set debuglevel = 1 (or higher) for http debug logging
from http.client import HTTPConnection
HTTPConnection.debuglevel = 0


# Expects context environment variables; see example-env.bash
# resolve workspace, warehouse and auth token from env (or fail)
HOST = os.getenv("HOST")
URL = os.getenv("URL")
if HOST and not URL:
    URL = f"https://{HOST}/api/2.0/sql/statements/"
WAREHOUSE = os.getenv("WAREHOUSE")
AUTH_TOKEN = os.environ.get("AUTH_TOKEN")
assert URL and WAREHOUSE and AUTH_TOKEN, "Required: HOST||URL, WAREHOUSE, and AUTH_TOKEN"


# example statement big enough to exceed 5MB data requirement
limit = None
sql_statement = "SELECT concat_ws('-', M.id, N.id, random()) as ID FROM range(1000) AS M, range(1000) AS N".format(limit)
if limit:
    sql_statement = "{sql_statement} LIMIT {limit}"

payload = json.dumps({
    "statement": sql_statement,
    "warehouse_id": WAREHOUSE,
    "wait_timeout": "0s",
    "disposition": "EXTERNAL_LINKS",
    "format": "ARROW_STREAM"
})

headers = {
    'Content-Type': 'application/json'
}
auth=('token', AUTH_TOKEN)

def process_success(response, limit=None):
    chunks = response.json()["manifest"]["chunks"]
    tables = []

    print("{} chunks(s) in result set".format(len(chunks)))
    for idx, chunkInfo in enumerate(chunks):
        stmt_url = urljoin(URL, statement_id) + "/"
        row_offset_param = urlencode({'row_offset': chunkInfo["row_offset"]})
        print(stmt_url)
        resolve_external_link_url = urljoin(stmt_url, "result/chunks/{}?{}".format(
            chunkInfo["chunk_index"], row_offset_param))

        response = requests.get(resolve_external_link_url, auth=auth, headers=headers)
        assert response.status_code == 200

        external_url = response.json()["external_links"][0]["external_link"]
        # NOTE: do _NOT_ send the authorization header to external urls
        raw_response = requests.get(external_url, auth=None, headers=None)
        assert raw_response.status_code == 200

        arrow_table = pyarrow.ipc.open_stream(raw_response.content).read_all()
        tables.append(arrow_table)
        print("chunk {} received".format(idx))

    full_table = pyarrow.concat_tables(tables).to_pandas()
    print(full_table)

print("Using URL:", URL)

response = requests.post(URL, auth=auth, headers=headers, data=payload)
print("Statement POST got HTTP status code:", response.status_code)
assert response.status_code == 200
state = response.json()["status"]["state"]
statement_id = response.json()["statement_id"]

while state in ["PENDING", "RUNNING"]:
    stmt_url = urljoin(URL, statement_id)
    response = requests.get(stmt_url, auth=auth, headers=headers)
    print("Statement GET got HTTP status code:", response.status_code)
    assert response.status_code == 200
    state = response.json()["status"]["state"]

assert state == "SUCCEEDED"
process_success(response, limit)

