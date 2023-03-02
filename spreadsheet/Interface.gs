const STATEMENT_ALL = `SELECT DATE_FORMAT(o_orderdate, "yyyy-MM") as year_month, year(o_orderdate) as year, month(o_orderdate) as month, sum(o_totalprice) as monthly_revenue FROM samples.tpch.orders GROUP BY year, month, year_month ORDER BY year, month,year_month;`

const TEMPLATE_STATEMENT = (order_date_start, order_date_end) => `SELECT DATE_FORMAT(o_orderdate, "yyyy-MM") as year_month, year(o_orderdate) as year, month(o_orderdate) as month, sum(o_totalprice) as monthly_revenue FROM samples.tpch.orders WHERE o_orderdate >= date('${order_date_start}') AND o_orderdate <= date('${order_date_end}') GROUP BY year, month, year_month ORDER BY year, month, year_month;`

const STATEMENT_CURRENT_YEAR= `SELECT DATE_FORMAT(o_orderdate, "yyyy-MM") as year_month, year(o_orderdate) as year, month(o_orderdate) as month, sum(o_totalprice) as monthly_revenue FROM samples.tpch.orders WHERE year(o_orderdate) == year(current_date()) GROUP BY year, month, year_month ORDER BY year, month, year_month;`

const STATEMENT_CURRENT_MONTH= `SELECT DATE_FORMAT(o_orderdate, "yyyy-MM") as year_month, year(o_orderdate) as year, month(o_orderdate) as month, sum(o_totalprice) as monthly_revenue FROM samples.tpch.orders WHERE year(o_orderdate) == year(current_date()) AND month(o_orderdate) == month(current_date()) GROUP BY year, month, year_month ORDER BY year, month, year_month;`

// Date range of interest for the samples.tpch.orders table; adjust to your use case.
const order_date_start = '1990-01-12';
const order_date_end = '1995-12-12';

const periods = ["Current month", "Current year", "Custom period"];

function onOpen() {
  createMenu();
}

function onEdit() {
  SpreadsheetApp.getActiveSpreadsheet().getActiveRange().setBackground('red');
  SpreadsheetApp.getActiveSpreadsheet().getActiveRange().setFontColor('white');
}

function createMenu() {
  var ui = SpreadsheetApp.getUi();
  ui.createMenu("Manage Orders")
    .addItem("Show all monthly orders", "allOrders")
    .addSeparator()
    .addItem("Choose order period", "showSidebar")
    .addSeparator()
    .addItem("Show query details (last)", "showInfo")
    .addToUi();
}

function allOrders() {
  var data = executeStatement(STATEMENT_ALL);

  if (data != null) { 
    var sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Orders").clearContents().clearFormats();
    sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
    sheet.getRange(1, 1, 1 , data[0].length).setFontWeight('bold');
    setLastQueryInfo({"Statement" : STATEMENT_ALL, "Status" : "SUCCESS", "Rows returned": data.length - 1});
  } else {
    setLastQueryInfo({"Statement" : STATEMENT_ALL, "Status" : "FAILED"});
  }
}

function customDatesOrders(customDateStart, customDateEnd) {
  var statement = TEMPLATE_STATEMENT(customDateStart, customDateEnd);

  var data = executeStatement(statement);

  if (data != null) { 
    sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Orders").clearContents().clearFormats();
    sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
    sheet.getRange(1, 1, 1 , data[0].length).setFontWeight('bold');
    setLastQueryInfo({"Statement" : statement, "Status" : "SUCCESS", "Rows returned": data.length - 1});
  } else {
    setLastQueryInfo({"Statement" : statement, "Status" : "FAILED"});
  }
}

function customPeriodOrders(period) {
  var data;
  var statement;
  if (period == periods[0]) {
    statement = STATEMENT_CURRENT_MONTH;
  } else {
    statement = STATEMENT_CURRENT_YEAR;
  }

  data = executeStatement(statement);

  if (data != null) { 
    sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Orders").clearContents().clearFormats();
    sheet.getRange(1, 1, data.length, data[0].length).setValues(data);
    sheet.getRange(1, 1, 1 , data[0].length).setFontWeight('bold');
    setLastQueryInfo({"Statement" : statement, "Status" : "SUCCESS", "Rows returned": data.length - 1});
  } else {
    setLastQueryInfo({"Statement" : statement, "Status" : "FAILED"});
  }
}

function showSidebar() {
  var ui = SpreadsheetApp.getUi();
  //var html = HtmlService.createHtmlOutputFromFile('sidebar');
  var hmtl = HtmlService.createTemplateFromFile('sidebar')
  .evaluate()
  .setTitle('Choose order period')
  .setSandboxMode(HtmlService.SandboxMode.IFRAME);
  ui.showSidebar(hmtl);
}

function showError(errorText) {
  Logger.log("The following error has occured: \n" + errorText);
  SpreadsheetApp.getUi().alert("The following error has occured: \n" + errorText);
}

function createInfoSheet() {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var sheet = ss.getSheetByName("Info Sheet");

  if (sheet == null) {
    sheet = ss.insertSheet();
    sheet.setName("Info sheet");
  }

  sheet.hideSheet();
  //sheet.showSheet()
  return sheet;
}

function setLastQueryInfo(obj) {
  var row = 0;
  var sheet = createInfoSheet().clearContents();

  for (const i in obj) {

    if (Object.hasOwn(obj, i)) {
      row++;
      sheet.getRange(`A${row}`).setValue(i);
      sheet.getRange(`B${row}`).setValue(obj[i]);
    }
  }

  sheet.getRange(`A${row+1}`).setValue("At");
  sheet.getRange(`B${row+1}`).setValue(getTimestamp());
}

function getTimestamp () {
    let date = new Date().toLocaleDateString();
    let time = new Date().toLocaleTimeString('en-US', { hour12: false, hour: "numeric", minute: "numeric"});
    return date + " " + time;
}

function showInfo () {
  var displayData = SpreadsheetApp.getActiveSpreadsheet().getSheetByName("Info Sheet").getDataRange().getValues();
  var ui = SpreadsheetApp.getUi();
  var t = HtmlService.createTemplateFromFile('info');

  t.data = displayData; 
  
  var html = t.evaluate()
  .setWidth(600)
  .setHeight(400);

  ui.showModalDialog(html, 'Query details');
}

