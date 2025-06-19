document.addEventListener("DOMContentLoaded", function () {
    let tooltips = document.querySelectorAll("[data-tooltip]");
    tooltips.forEach(function (el) {
        el.setAttribute("title", el.getAttribute("data-tooltip"));
        el.classList.add("has-tooltip");
    });
});