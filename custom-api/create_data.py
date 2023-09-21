import os

# Databricks SDK
from databricks.sdk import WorkspaceClient
from databricks.sdk.service.sql import *

# Initialize Databricks SDK. 
# By default, this authenticates using the DATABRICKS_HOST and DATABRICKS_TOKEN environment variables
# initialized by setup.sh.
w = WorkspaceClient()

warehouse_id = os.environ.get("DATABRICKS_WAREHOUSE_ID")

# This script uses the Statement Execution API to generate sample data.

def execute_statement_sync(sql_statement):
  response = w.statement_execution.execute_statement(
    statement = sql_statement,
    warehouse_id = warehouse_id
  )

  while response.status.state in (StatementState.PENDING, StatementState.RUNNING):
    response = w.statement_execution.get_statement(statement_id = response.statement_id)

  if response.status.state != StatementState.SUCCEEDED:
    print("Failed to execute: '" + sql_statement + "' with state " + str(response.status.state));
    if response.status.state == StatementState.FAILED:
        print("Detailed error message: " + response.status.error.message)
    exit()

  return

# Create the stores table.
print("Creating acme_demo_stores table.")
execute_statement_sync(
    """
      CREATE TABLE acme_demo_stores (
        id INT,
        name VARCHAR(10),
        manager VARCHAR(5),
        employee_count INT,
        city VARCHAR(10),
        state VARCHAR(2)
        );
    """
)

# Generate random data for the stores table.
print("Inserting data into acme_demo_stores table.")
execute_statement_sync(
    """
      INSERT INTO acme_demo_stores
        SELECT 
            CAST(RAND()*1000 AS INT),
            CONCAT(CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65)),
            CONCAT(CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65)),
            RAND()*1000,
            CONCAT(CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65)),
            CONCAT(CHAR(FLOOR(RAND()*26)+65), CHAR(FLOOR(RAND()*26)+65))
        FROM (
            SELECT 1 AS number UNION ALL
            SELECT 2 AS number UNION ALL
            SELECT 3 AS number UNION ALL
            SELECT 4 AS number UNION ALL
            SELECT 5 AS number UNION ALL
            SELECT 6 AS number UNION ALL
            SELECT 7 AS number UNION ALL
            SELECT 8 AS number UNION ALL
            SELECT 9 AS number UNION ALL
            SELECT 10 AS number
        ) a
        CROSS JOIN (
            SELECT 1 AS number UNION ALL
            SELECT 2 AS number UNION ALL
            SELECT 3 AS number UNION ALL
            SELECT 4 AS number UNION ALL
            SELECT 5 AS number UNION ALL
            SELECT 6 AS number UNION ALL
            SELECT 7 AS number UNION ALL
            SELECT 8 AS number UNION ALL
            SELECT 9 AS number UNION ALL
            SELECT 10 AS number
        ) b;
    """
)

# Create sales table.
print("Creating acme_demo_sales table.")
execute_statement_sync(
    """
      CREATE TABLE acme_demo_sales (
        id BIGINT,
        date DATE,
        store_id INT,
        item_id INT,
        quantity INT,
        price DECIMAL(7,2)
        );
    """
)

# Generate random data for the sales table.
print("Inserting data into acme_demo_sales table.")
execute_statement_sync(
    """
      INSERT INTO acme_demo_sales
        SELECT 
            RAND()*100000,
            CAST(DATEADD(day, RAND()*365, '2020-01-01') AS DATE),
            i.id,
            RAND()*1000,
            RAND()*1000,
            CAST(RAND()*1000 AS DECIMAL(7,2))
        FROM (
            SELECT id, ROW_NUMBER() OVER (ORDER BY id) - 1 AS row_number FROM acme_demo_stores
        ) i
        JOIN (
            SELECT 1 AS row_number UNION ALL
            SELECT 2 AS row_number UNION ALL
            SELECT 3 AS row_number UNION ALL
            SELECT 4 AS row_number UNION ALL
            SELECT 5 AS row_number UNION ALL
            SELECT 6 AS row_number UNION ALL
            SELECT 7 AS row_number UNION ALL
            SELECT 8 AS row_number UNION ALL
            SELECT 9 AS row_number UNION ALL
            SELECT 10 AS row_number
        ) r
        ON r.row_number <= (SELECT COUNT(*) FROM acme_demo_stores);
    """
)
