function displayError(message) {
  var errorContainer = $("#error-container");
  errorContainer.text("Error: " + message);
  errorContainer.show();
}

function showLoadingIcon() {
  $('#loading-icon').show();
}

function hideLoadingIcon() {
  $('#loading-icon').hide();
}

function showDownloadLoadingIcon() {
  $('#download-loading-icon').show();
}

function hideDownloadLoadingIcon() {
  $('#download-loading-icon').hide();
}
