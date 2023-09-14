//
// Pagination code that returns 10 rows at a time and generates page links.
//

// Module variables that cache data/metadata for pagination.
var globalStoreData = null
var globalPageCount = null
const globalPageSize = 10;

function setPaginationData(data) {
  globalStoreData = data;
  globalPageCount = Math.ceil(globalStoreData.length / globalPageSize);              
}

function getPageData(pageIndex) {
  var rowOffset = pageIndex * globalPageSize;
  return globalStoreData.slice(rowOffset, rowOffset + globalPageSize)
}

function updatePaginationLinks(currentPage) {        
  var paginationLinks = '';
  var maxVisibleLinks = 3;
  var lastPage = globalPageCount - 1;

  // Add Previous page link
  if (currentPage > 0) {
    paginationLinks += '<li><a href="#" class="page-link" data-page="' + (currentPage - 1) + '">Prev</a></li>';
  }

  // Add First page
  if (currentPage === 0) {
    paginationLinks += '<li><span class="current">0</span></li>';
  } else if (currentPage > 0) {
    paginationLinks += '<li><a href="#" class="page-link" data-page="0">0</a></li>';
  }

  // Add "..." before current page if necessary
  if (currentPage >= maxVisibleLinks) {
    paginationLinks += '<li><span class="ellipsis">...</span></li>';
  }

  // Calculate the range of visible pages
  var startPage = Math.max(1, currentPage - Math.floor(maxVisibleLinks / 2));
  var endPage = Math.min(lastPage - 1, startPage + maxVisibleLinks - 1);

  // Generate page links within the range
  for (var i = startPage; i <= endPage; i++) {
    if (i === currentPage) {
      paginationLinks += '<li><span class="current">' + i + '</span></li>';
    } else {
      paginationLinks += '<li><a href="#" class="page-link" data-page="' + i + '">' + i + '</a></li>';
    }
  }

  // Add "..." after current page if necessary
  if (endPage < (lastPage - 1)) {
    paginationLinks += '<li><span class="ellipsis">...</span></li>';
  }

  // Add Last page link
  if (currentPage === lastPage) {
    paginationLinks += '<li><span class="current">' + lastPage + '</span></li>';
  } else if (currentPage < lastPage) {
    paginationLinks += '<li><a href="#" class="page-link" data-page="' + lastPage + '">' + lastPage + '</a></li>';
  }

  // Add Next page link
  if (currentPage < lastPage) {
    paginationLinks += '<li><a href="#" class="page-link" data-page="' + (currentPage + 1) + '">Next</a></li>';
  }

  $('#pagination-links').html(paginationLinks);
}
