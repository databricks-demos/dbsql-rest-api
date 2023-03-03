// Go to the Connection details page of your warehouse to set the parameters below
const HOST = "<server_hostname>";
const WAREHOUSE = "<warehouse_id>";
const AUTH_TOKEN = "<your_personal_auth_token>";

const WAIT_TIMEOUT = "50s";       
const ON_WAIT_TIMEOUT = "CANCEL";

const HTTP_REQUEST_BASE = {
  headers: {
    Authorization: `Bearer ${AUTH_TOKEN}`,
  },
  contentType: "application/json",
  method: "GET",
  payload: null,
  muteHttpExceptions: true,
};

function fetchFromUrl(url, request) {
   try {
     let response = UrlFetchApp.fetch(url, request);
     let responseJson = JSON.parse(response);
     let statusCode = response.getResponseCode();
     switch (statusCode) {
      case 200:
         return responseJson;
      default:
         showError(`Error: code=${responseJson["error_code"]} message=${responseJson["message"]}`);
         return null;
     }
   } catch (error) {
     showError(`Error: error=${error}`);
     return null;
   }
}

function submitStatement(statement) {
  let body = {
    "statement": statement,
    "warehouse_id": WAREHOUSE,
    "wait_timeout": "10s",
    "on_wait_timeout": "CONTINUE",
  };

  let request = Object.assign({}, HTTP_REQUEST_BASE, { method: "POST", payload: JSON.stringify(body) });
  let response = fetchFromUrl(`https://${HOST}/api/2.0/sql/statements`, request);
  if (response.status.state == "FAILED") {
      showError(`Submit request failed with unexpected state: ${response.status.state}`)
      return null;
  } 

  return response;
}

function checkStatus(statement_id) {
  let response = fetchFromUrl(`https://${HOST}/api/2.0/sql/statements/${statement_id}`, HTTP_REQUEST_BASE);
  if (response.status.state == "FAILED") {
      let error = responseJson["status"]["error"]
      showError(`Fetch request failed: code=${error["error_code"]} message=${error["message"]}`);
      return null;
  }
  return response;
}

function handleResult(manifest, result) {
  // Response contains first chunk of rows; check below whether there are more.
  var columnNames = manifest["schema"]["columns"].map(col => col["name"]);
  var chunks = [result.data_array];

  while (result["next_chunk_internal_link"]) {
    chunk = result["next_chunk_internal_link"];
    result = fetchFromUrl(`https://${HOST}${chunk}`, HTTP_REQUEST_BASE);
    chunks.push(result["data_array"]);
  }

  // prepare response: rows[0] = column names
  return [[columnNames]].concat(chunks).flat()
}

function executeStatement(statement) {
  var response = submitStatement(statement);

  if (response.status.state == "SUCCEEDED") {
    return handleResult(response.manifest, response.result);
  } else {
    response = checkStatus(response.statement_id);
    while (response.status.state == "PENDING" || response.status.state == "RUNNING") {
      response = checkStatus(response.statement_id)
    }

    return handleResult(response.manifest, response.result);
  }
}

function testExecuteStatementSync() {
  let rows = executeStatement("SELECT 1");
  Logger.log(`rows[0] = ${rows[0]}`);
}

