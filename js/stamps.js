/* made-stamp: fill in a live "N days ago" so static dates never go stale */
(function () {
  var DAY = 86400000;
  document.querySelectorAll(".made-stamp[data-last]").forEach(function (el) {
    var span = el.querySelector(".made-stamp__ago");
    if (!span) return;
    var p = el.getAttribute("data-last").split("-");
    var last = new Date(+p[0], p[1] - 1, +p[2]);          // local midnight
    var now = new Date();
    var today = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    var days = Math.round((today - last) / DAY);
    var ago = days <= 0 ? "today" : days === 1 ? "yesterday" : days + " days ago";
    span.textContent = " · " + ago;
  });
})();
