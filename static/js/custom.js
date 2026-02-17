
// console.log("✅ custom.js loaded");








// function num(x) {
//   const n = Number(x);
//   return Number.isFinite(n) ? n : 0;
// }

// function escapeHtml(s) {
//   return String(s ?? "")
//     .replaceAll("&", "&amp;")
//     .replaceAll("<", "&lt;")
//     .replaceAll(">", "&gt;")
//     .replaceAll('"', "&quot;")
//     .replaceAll("'", "&#039;");
// }

// function shortInn(inn) {
//   const x = String(inn ?? "").replace(/\D/g, "");
//   return x ? x : "—";
// }

// function formatRuDate(value) {
//   const d = new Date(value);
//   if (Number.isNaN(d.getTime())) return String(value || "");
//   return new Intl.DateTimeFormat("ru-RU", {
//     day: "2-digit",
//     month: "long",
//     year: "numeric",
//     weekday: "long",
//   }).format(d);
// }

// // -------------------------------------------------
// // 1)  логика раскрытия/сворачивания карточки
// // -------------------------------------------------
// document.addEventListener("click", function (event) {
//   const header = event.target.closest(".valuation-inline__header");
//   if (!header) return;

//   const box = header.closest(".valuation-inline");
//   if (!box) return;

//   if (box.classList.contains("is-collapsed")) {
//     box.classList.remove("is-collapsed");
//     box.classList.add("is-open");
//   } else {
//     box.classList.add("is-collapsed");
//     box.classList.remove("is-open");
//   }
// });

// // -------------------------------------------------
// // 2) Jazzmin topmenu: ИКОНКИ БЕЗ ТЕКСТА 
// // -------------------------------------------------
// (function () {
//   // Важно: ключи должны совпадать с видимым текстом ссылок в topmenu_links
//   const ICONS = {
//     Home: "fa-solid fa-house",
//     Пользователи: "fa-solid fa-users",
//     "Дневные Продажи": "fa-solid fa-calendar-days",
//     "Upload Form": "fa-solid fa-cloud-arrow-up",
//     "Redis update": "fa-solid fa-arrows-rotate",
//   };

//   // Берём только ЛЕВОЕ меню, чтобы не трогать правые иконки (юзер/приложения)
//   function getTopmenuLinks() {
//     const leftUl = document.querySelector(".main-header .navbar-nav:first-child");
//     if (!leftUl) return [];
//     return Array.from(leftUl.querySelectorAll(".nav-link"));
//   }

//   function enhanceTopMenu() {
//     const links = getTopmenuLinks();
//     if (!links.length) return;

//     links.forEach((a) => {
      
//       if (a.classList.contains("jm-toplink")) return;

//       const rawText = (a.textContent || "").replace(/\s+/g, " ").trim();
//       if (!rawText) return;

//       const iconClass = ICONS[rawText];
//       if (!iconClass) return;

//       a.classList.add("jm-toplink");
//       a.textContent = "";

//       const ico = document.createElement("span");
//       ico.className = "jm-ico";
//       ico.innerHTML = `<i class="${iconClass}" aria-hidden="true"></i>`;
//       a.appendChild(ico);


//       a.setAttribute("title", rawText);
//       a.setAttribute("aria-label", rawText);
//     });
//   }

//   function boot() {
//     enhanceTopMenu();
//   }

//   document.addEventListener("DOMContentLoaded", boot);
//   document.addEventListener("pjax:end", boot);
// })();





console.log("✅ custom.js loaded");

// -------------------------------------------------
// 0) Подключаем admin_custom.js (Jazzmin у тебя не умеет список custom_js)
// -------------------------------------------------
(function loadAdminCustomJs() {
  const src = "/static/js/admin_custom.js";

  // не грузим повторно
  const already = Array.from(document.scripts).some((s) =>
    (s.src || "").includes("admin_custom.js")
  );
  if (already) return;

  const s = document.createElement("script");
  s.src = src;
  s.defer = true;
  s.onload = () => console.log("✅ admin_custom.js loaded");
  s.onerror = () => console.warn("❌ admin_custom.js NOT loaded:", src);
  document.head.appendChild(s);
})();

function num(x) {
  const n = Number(x);
  return Number.isFinite(n) ? n : 0;
}

function escapeHtml(s) {
  return String(s ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function shortInn(inn) {
  const x = String(inn ?? "").replace(/\D/g, "");
  return x ? x : "—";
}

function formatRuDate(value) {
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return String(value || "");
  return new Intl.DateTimeFormat("ru-RU", {
    day: "2-digit",
    month: "long",
    year: "numeric",
    weekday: "long",
  }).format(d);
}

// -------------------------------------------------
// 1) логика раскрытия/сворачивания карточки
// -------------------------------------------------
document.addEventListener("click", function (event) {
  const header = event.target.closest(".valuation-inline__header");
  if (!header) return;

  const box = header.closest(".valuation-inline");
  if (!box) return;

  if (box.classList.contains("is-collapsed")) {
    box.classList.remove("is-collapsed");
    box.classList.add("is-open");
  } else {
    box.classList.add("is-collapsed");
    box.classList.remove("is-open");
  }
});

// -------------------------------------------------
// 2) Jazzmin topmenu: ИКОНКИ БЕЗ ТЕКСТА
// -------------------------------------------------
(function () {
  // Важно: ключи должны совпадать с видимым текстом ссылок в topmenu_links
  const ICONS = {
    Home: "fa-solid fa-house",
    Пользователи: "fa-solid fa-users",
    "Дневные Продажи": "fa-solid fa-calendar-days",
    "Upload Form": "fa-solid fa-cloud-arrow-up",
    "Redis update": "fa-solid fa-arrows-rotate",
  };

  // Берём только ЛЕВОЕ меню, чтобы не трогать правые иконки (юзер/приложения)
  function getTopmenuLinks() {
    const leftUl = document.querySelector(".main-header .navbar-nav:first-child");
    if (!leftUl) return [];
    return Array.from(leftUl.querySelectorAll(".nav-link"));
  }

  function enhanceTopMenu() {
    const links = getTopmenuLinks();
    if (!links.length) return;

    links.forEach((a) => {
      if (a.classList.contains("jm-toplink")) return;

      const rawText = (a.textContent || "").replace(/\s+/g, " ").trim();
      if (!rawText) return;

      const iconClass = ICONS[rawText];
      if (!iconClass) return;

      a.classList.add("jm-toplink");
      a.textContent = "";

      const ico = document.createElement("span");
      ico.className = "jm-ico";
      ico.innerHTML = `<i class="${iconClass}" aria-hidden="true"></i>`;
      a.appendChild(ico);

      a.setAttribute("title", rawText);
      a.setAttribute("aria-label", rawText);
    });
  }

  function boot() {
    enhanceTopMenu();
  }

  document.addEventListener("DOMContentLoaded", boot);
  document.addEventListener("pjax:end", boot);
})();
