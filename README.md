# DBSQL REST API

This repository includes code samples that use the DBSQL REST API.

## The Spreadsheet application

To setup the Spreadsheet application follow these steps:

1. Create a new Google Spreadsheet file called `Orders`. 

2. Inside, create a sheet called `Orders`.

3. Navigate to `Extensions -> Apps Script` and rename the script to `Orders`.

4. In the Apps Script editor, create four files with the names and content of the files located in the `spreadsheet` folder: `Interface.gs`, `DBSQL.gs`, `sidebar.html`, and `info.html`.

5. Inside the `DBSQL.gs` file, provide the connectivity parameters for the Databricks server: `HOST`, `WAREHOUSE_ID`, and `AUTH_TOKEN`. 

6. Save the files.

7. Go back to your Spreadsheet and refresh it.

8. You will now get a `Managed Orders` menu next to the `Extensions` menu.

9. Select `Managed Orders -> Show Monthly Orders` and accept the authorization request.

10. To configure the permissions in your sheet, select `Project Settings -> Show appscript.json manifest file in editor`.

11. This will show a new file in the App Script workspace where you can edit the grants. See more [details](https://developers.google.com/identity/protocols/oauth2/scopes#sheets).

12. You are now all set. Run the predefined queries using the entries in the `Managed Orders` menu.

## The Postman collection

The Postman collection consists of two `json` files `Databricks Environment.postman_environment.json` and `Databricks SQL Execution API.postman_collection.json`. The former can be used to define environment variables needed to establish connection with the Databricks server: `HOST`, `WAREHOUSE_ID`, and `AUTH_TOKEN`. The latter includes several API requests using the sync and async flows.

To use the Postman collection follow the steps below:

1. Open Postman, go to `My Workspace` and click Import to add the two files.

2. Go to `Environments` and select `Databricks Environment` to update the connection parameters. Make sure to save the changes.

3. Select the `Databricks Enviroment` from the environment selector.

4. Run one of the API requests for executing statements.

5. Use the GET requests to poll for status and fetch chunks.


## External links with Python
The Python script executes a statement in asynchronous mode with `disposition` and `format` set to `EXTERNAL_LINKS` and `ARROW_STREAM`, respectively. Then, it retrieves each chunk using the presigned URL, deserializes the Arrow bytes and converts the result into a pandas `DataFrame`.

