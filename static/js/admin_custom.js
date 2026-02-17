console.log("✅ admin_custom.js loaded");

(function () {
  function insertBell() {
    console.log("🔎 trying to insert bell…");

    // Берём именно тот UL, где уже есть твои topmenu-иконки.
    // В Jazzmin это обычно первый .navbar-nav внутри .main-header
    const nav = document.querySelector(".main-header .navbar-nav");
    console.log("nav found:", !!nav, nav);

    if (!nav) return;

    // Не вставляем второй раз
    if (document.getElementById("jmBellDropdown")) {
      console.log("🔔 bell already exists");
      return;
    }

    const li = document.createElement("li");
    li.className = "nav-item dropdown";
    li.id = "jmBellDropdown";

    li.innerHTML = `
      <a class="nav-link" href="#" id="jmBellLink" title="Контроль номенклатуры">
        <i class="fas fa-bell"></i>
        <span id="alertsBadge" class="badge badge-danger navbar-badge" style="display:none;">0</span>
        
      </a>

      <div class="dropdown-menu dropdown-menu-right" id="jmBellMenu" style="min-width:320px;">
        <span class="dropdown-item dropdown-header">Контроль справочников</span>
        <div class="dropdown-divider"></div>

        <a href="/admin/corporate/items/?subcat__isnull=1" class="dropdown-item">
          <i class="fas fa-layer-group mr-2"></i>
          Без подкатегории
          <span id="noSubcatBadge" class="float-right badge badge-warning">0</span>
        </a>

        <div class="dropdown-divider"></div>

        <a href="/admin/corporate/items/?cat__isnull=1" class="dropdown-item">
          <i class="fas fa-folder-open mr-2"></i>
          Без категории
          <span id="noCatBadge" class="float-right badge badge-warning">0</span>
        </a>
      </div>
    `;

    nav.appendChild(li);
    console.log("✅ bell inserted");

    // dropdown вручную (без bootstrap)
    const bellLink = document.getElementById("jmBellLink");
    const menu = document.getElementById("jmBellMenu");

    function closeMenu() { menu.classList.remove("show"); }
    function toggleMenu() { menu.classList.toggle("show"); }

    bellLink.addEventListener("click", function (e) {
      e.preventDefault();
      e.stopPropagation();
      toggleMenu();
    });
    menu.addEventListener("click", (e) => e.stopPropagation());
    document.addEventListener("click", closeMenu);

    // подтягиваем счётчики
    async function refresh() {
      try {
        const r = await fetch("/admin/alerts-counts/", { credentials: "same-origin" });
        console.log("alerts-counts status:", r.status);
        if (!r.ok) return;
        const data = await r.json();
        console.log("alerts data:", data);

        const noSubcat = Number(data.no_subcat || 0);
        const noCat = Number(data.no_cat || 0);
        const total = noSubcat + noCat;

        const topBadge = document.getElementById("alertsBadge");
        document.getElementById("noSubcatBadge").textContent = noSubcat;
        document.getElementById("noCatBadge").textContent = noCat;

        if (total > 0) {
          topBadge.style.display = "inline-block";
          topBadge.textContent = total;
        } else {
          topBadge.style.display = "none";
        }
      } catch (e) {
        console.warn("refresh error:", e);
      }
    }

    refresh();
    setInterval(refresh, 60000);
  }

  // пробуем несколько раз (на случай PJAX/поздней отрисовки navbar)
  document.addEventListener("DOMContentLoaded", insertBell);
  document.addEventListener("pjax:end", insertBell);
  setTimeout(insertBell, 500);
  setTimeout(insertBell, 1500);
})();
