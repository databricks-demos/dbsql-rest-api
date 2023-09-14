from flask import Flask, request, jsonify, render_template
from enum import Enum
import os
import requests
import json
import random
import subprocess
import threading
import time

# Databricks SDK
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import *

# Initialize Databricks SDK. 
# By default, this authenticates using the DATABRICKS_HOST and DATABRICKS_TOKEN environment variables
# initialized by setup.sh.
w = WorkspaceClient()

warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")

app = Flask(__name__)

#
# Store the parameterized SQL statements used to read/write data to Databricks SQL.
#
class SqlStatement(Enum):
    LIST_STORES = 1
    LIST_SALES = 2
    INSERT_SALE = 3

sql_statements = {
     SqlStatement.LIST_STORES: """
            select
                id,
                name, 
                manager,
                employee_count
                city,
                state
            from 
                hive_metastore.acme_demo.stores
        """,
    SqlStatement.LIST_SALES: """
            select 
                date,
                id,
                store_id,
                item_id,
                quantity,
                price
            from 
                hive_metastore.acme_demo.sales
            where
                store_id = :store_id
            order by
                date desc
        """,
    SqlStatement.INSERT_SALE: """
            INSERT INTO
              hive_metastore.acme_demo.sales (
                date,
                id,
                store_id,
                item_id,
                price,
                quantity
              )
            VALUES
              (
                :sold_date,
                :sale_id, 
                :store_id,
                :item_id,
                :price,
                :quantity
              )
        """
}

#
# Web Endpoints
#
@app.route("/")
def index():
    return render_template("stores.html")

@app.route("/stores/<string:store_id>")
def customer(store_id):
    return render_template("store.html", store_id=store_id)

@app.route("/newsale")
def newSale():
    return render_template("new_sale.html")

#
# Custom API Endpoints
#

#
# Endpoint to list store information.
#
# It takes no arguments and invokes the Statement Execution API in synchronous mode, returning store data results in
# JSON format. If the request to Databricks SQL takes longer than 50 seconds, the execution will be cancelled and no
# data is returned.
#
@app.route("/api/1.0/stores", methods=["GET"])
def list_stores():
    statement_response = w.statement_execution.execute_statement(
        statement = sql_statements[SqlStatement.LIST_STORES],
        wait_timeout = "50s",
        on_wait_timeout = TimeoutAction.CANCEL,
        warehouse_id = warehouse_id
    )

    stores = None
    if statement_response.status.state == StatementState.SUCCEEDED:
        stores = statement_response.result.data_array
    else:
        print(statement_response.status)

    response = {
        'state': str(statement_response.status.state.name),
        'stores': stores 
    }
    
    return jsonify(response)

#
# Endpoint to list sales for a specific store.
#
# This invokes the Statement Execution API in asynchronous mode, returning an ID the client can use to poll on status.
# Once the status is SUCCEEDED, the number of result chunks is returned to the caller. Then, in a parallel, the caller
# can get external links for each chunk and download the data from cloud storage.
#
# Arguments:
#   store_id - Required ID of the store supplied in the URL.
#   request_id - Optional ID used to poll for status on a request.
#   chunk_index - Optional chunk index that can be used to get an external link to data for a successful request.
#
# Return Values:
#   request_id - Returned for all successfully accepted requests. Used this ID to poll for completion status.
#   state - Returned on the initial request and status polls. Can be PENDING, RUNNING, SUCCEEDED, FAILED, CANCELED,
#           or CLOSED.
#   chunk_count - Returned for successful requests, indicating how many chunks of sales data there are for the store.
#   link - A pre-signed URL returned when a request_id and chunk_index are supplied as arguments.
#   
@app.route("/api/1.0/stores/<string:store_id>/sales", methods=["GET"])
def list_sales_async(store_id):
    # If a request ID is not supplied, execute a new list request.
    request_id = request.args.get('request_id')
    chunk_index = request.args.get('chunk_index')
    if request_id is None:
        # Get the format from the request. It can be ‘CSV’, ‘JSON_ARRAY’, or ‘ARROW_STREAM’
        format = request.args.get('format')
        row_limit = request.args.get('row_limit')
        response = execute_list_sales_request(store_id, format, row_limit)
        
    # If there is no chunk index, poll for status.
    elif chunk_index is None:
        response = get_list_sales_status(request_id)

    # Otherwise return the pre-signed URL for the specified chunk.
    else:
        response = get_list_sales_chunk(request_id, chunk_index)
        
    return jsonify(response)

# Invoke the Statement Execution API in asynchronous mode, returning an ID so the client can poll on status.
def execute_list_sales_request(store_id, format, row_limit):
    # Use parameters to prevent SQL injection via the store ID string.
    parameters = [
        StatementParameterListItem(name='store_id', value=store_id, type="INT")
    ]

    statement_response = w.statement_execution.execute_statement(
        statement = sql_statements[SqlStatement.LIST_SALES],
        format = Format[format],
        disposition = Disposition.EXTERNAL_LINKS,
        wait_timeout = "0s",
        warehouse_id = warehouse_id,
        parameters = parameters,
        row_limit = row_limit,
        byte_limit = 500000000 # 500MB limit because lcp crashes.
        )

    response = {
        'request_id': statement_response.statement_id,
        'state': str(statement_response.status.state.name)
    }

    return response

# Poll the Statement Execution API for status on a previously generated execution request.
def get_list_sales_status(request_id):
    statement_response = w.statement_execution.get_statement(statement_id = request_id)
    response = {
        'request_id': statement_response.statement_id,
        'state': str(statement_response.status.state.name)
    }

    if statement_response.status.state == StatementState.SUCCEEDED:
        response['chunk_count'] = statement_response.manifest.total_chunk_count

    return response

# Get the external link for the given chunk. The pre-signed URL is valid for 15 mins.
def get_list_sales_chunk(request_id, chunk_index):
    result_data = w.statement_execution.get_statement_result_chunk_n(
        statement_id = request_id,
        chunk_index = chunk_index
    )

    response = {
        'request_id': request_id,
        'link': rewrite_external_link(result_data.external_links[0].external_link)
    }

    return response

#
# Endpoint to add a sale to a store.
#
# This endpoint uses a parameterized query to insert data in to the Lakehouse via the Statement Execution API.
#
# Arguments:
#   store_id - Required ID of the store supplied in the URL.
#   date - Required date of the day the sale took place.
#   price - Required price of each item sold.
#   quantity - Required number of items sold.
#   item-id - Required ID for the item sold.
#   
@app.route("/api/1.0/stores/<string:store_id>/sales", methods=["POST"])
def insert_sale(store_id):
    sold_date = request.form.get('date')
    sales_price = request.form.get('price')
    quantity = request.form.get('quantity')
    item_id = request.form.get('item-id')
    sale_id = random.getrandbits(32)
    parameters = [
        StatementParameterListItem(name='sold_date', value=sold_date, type="DATE"),
        StatementParameterListItem(name='sale_id', value=sale_id, type="BIGINT"),
        StatementParameterListItem(name='store_id', value=store_id, type="INT"),
        StatementParameterListItem(name='item_id', value=item_id, type="INT"),
        StatementParameterListItem(name='quantity', value=quantity, type="INT"),
        StatementParameterListItem(name='price', value=sales_price, type="DECIMAL(7,2)")
    ]

    statement_response = w.statement_execution.execute_statement(
        statement = sql_statements[SqlStatement.INSERT_SALE],
        wait_timeout = "50s",
        on_wait_timeout = TimeoutAction.CONTINUE,
        warehouse_id = warehouse_id,
        parameters = parameters
        )

    response = {
        'state': str(statement_response.status.state.name),
        'sale_id': sale_id
    }

    return jsonify(response)

#
# WARNING: Don't use in production.
# 
# The following is needed to overcome CORS without Databricks workspace bucket modifications.
#
local_cors_proxy_lock = threading.Lock()
local_cors_proxy_enabled = False

def get_host(external_link):
    # Check for .com and .net.
    dot_com_index = external_link.find(".com")
    if dot_com_index != -1:
        return external_link[:dot_com_index+len(".com")]
    
    dot_net_index = external_link.find(".net")
    if dot_net_index != -1:
        return external_link[:dot_net_index+len(".net")]
    
    return external_link

def rewrite_external_link(external_link):
    global local_cors_proxy_enabled
    external_link_host = get_host(external_link)
    # Synchronize to make sure the cors proxy is enabled.
    with local_cors_proxy_lock:
        if local_cors_proxy_enabled is False:
            subprocess.Popen(['lcp', '--proxyUrl', external_link_host])
            local_cors_proxy_enabled = True

    return external_link.replace(external_link_host, "http://localhost:8010/proxy")

if __name__ == "__main__":
    app.run()
