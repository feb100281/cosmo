(function () {
  // Полностью глушим HTML5 drag'n'drop на странице changelist
  document.addEventListener("dragstart", function (e) {
    e.preventDefault();
    e.stopPropagation();
    return false;
  }, true);

  document.addEventListener("drop", function (e) {
    e.preventDefault();
    e.stopPropagation();
    return false;
  }, true);

  document.addEventListener("dragover", function (e) {
    e.preventDefault();
    e.stopPropagation();
    return false;
  }, true);
})();
