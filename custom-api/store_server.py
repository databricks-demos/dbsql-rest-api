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
# By default, this authenticates using DATABRICKS_HOST and DATABRICKS_TOKEN environment variables.
w = WorkspaceClient()

warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")

app = Flask(__name__)

# Store the parameterized SQL statements used to read/write data to Databricks SQL.
class SqlStatement(Enum):
    LIST_STORES = 1
    LIST_SALES = 2
    INSERT_SALE = 3

sql_statements = {
     SqlStatement.LIST_STORES: """
            select
                s_store_sk as store_id, 
                s_store_name as store_name, 
                s_manager as manager,
                s_number_employees as number_employees, 
                s_city as city,
                s_state as state
            from 
                chris_stevens.retail.store
        """,
    SqlStatement.LIST_SALES: """
            select 
                ss_sold_date_sk,
                ss_ticket_number,
                ss_store_sk,
                ss_item_sk,
                ss_quantity,
                ss_sales_price
            from 
                chris_stevens.retail.store_sales
            where
                ss_store_sk = :store_id
            order by
                ss_sold_date_sk desc
        """,
    SqlStatement.INSERT_SALE: """
            INSERT INTO chris_stevens.retail.store_sales (ss_sold_date_sk, ss_ticket_number, ss_store_sk, ss_item_sk, ss_sales_price, ss_quantity) 
            VALUES (:sold_date, :sale_id, :store_id, :item_id, :sales_price, :quantity)
        """
}

# Web Endpoints
@app.route("/")
def index():
    return render_template("stores.html")

@app.route("/stores/<string:store_id>")
def customer(store_id):
    return render_template("store.html", store_id=store_id)

@app.route("/newsale")
def newSale():
    return render_template("new_sale.html")

# API Endpoints

# Endpoint to list store information.
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

def get_list_sales_status(request_id):
    statement_response = w.statement_execution.get_statement(statement_id = request_id)
    response = {
        'request_id': statement_response.statement_id,
        'state': str(statement_response.status.state.name)
    }

    if statement_response.status.state == StatementState.SUCCEEDED:
        response['chunk_count'] = statement_response.manifest.total_chunk_count

    return response

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
        StatementParameterListItem(name='sales_price', value=sales_price, type="DECIMAL(7,2)")
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
    
# WARNING: Don't use in production.
# 
# The following is needed to overcome CORS without workspace bucket modifications.
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
