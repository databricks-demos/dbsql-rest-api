# Custom API for Acme, Inc.

The purpose of this demo is to demonstrate building a custom API on top of the Databricks SQL Statement Execution API. By following this example you will learn how to:

1. Use the SQL Statement Execution API in sync, async, and hybrid (i.e. sync with fallback to async) modes.
2. Safely include user input in your SQL statements with parameterized queries.
3. Download large results in parallel using EXTERNAL_LINKS.
4. Use the [Databricks SDK for Python](https://github.com/databricks/databricks-sdk-py) to invoke the SQL Statement Execution API.

## Overview

This demo includes a Flask web server as a backend and an HTML/JQuery front end. The backend serves both the font end web pages and the custom data API. The custom API wraps the SQL Statement Execution API using the Databricks SDK for Python. The custom API has three endpoints:

* `GET /api/1.0/stores` - lists Acme, Inc's stores.
* `GET /api/1.0/stores/<store_id>/sales` - lists sales for a given store.
* `POST /api/1.0/stores/<store_id>/sales` - creates a new sale for a given store.

## Setup

1. Run the setup script: `source ./setup.sh`
    - Installs Flask
    - Installs the Databricks SDK for Python
    - Installs [Local CORS Proxy](https://www.npmjs.com/package/local-cors-proxy)
        - This is use to overcome [CORS](https://en.wikipedia.org/wiki/Cross-origin_resource_sharing) errors in the demo. Not required for production.
    - Initializes Databricks host, token, and Warehouse ID environment variables.
    - Creates sample tables in your hive metastore. The size is < 50KB.
        - This is a significantly smaller data set that we used in the Data+AI Summit demo.
2. Run the app: `python3 acme_server.py`
3. Visit http://127.0.0.1:5000 in your browser.

# Known Issues

1. If you get a 403 when loading a page in Chrome, go to `chrome://net-internals/#sockets` and click "Flush socket pools". This is an issue with Flask.