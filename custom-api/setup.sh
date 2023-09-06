#!/bin/bash

# Install dependencies.
pip3 install flask
pip3 install databricks-sdk
npm install -g local-cors-proxy

# Get the Databricks HOST.
echo "Enter your Databricks HOST (i.e. foo.databricks.com):"
read HOST
echo
export DATABRICKS_HOST=$HOST

# Get the access token.
echo "Enter your Databricks personal access token:"
read TOKEN
echo
export DATABRICKS_TOKEN=$TOKEN

# Get the Warehouse ID
echo "Enter your Databricks SQL Warehouse ID:"
read WAREHOUSE_ID
echo
export DATABRICKS_WAREHOUSE_ID=$WAREHOUSE_ID