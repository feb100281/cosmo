# store_logos.py

STORE_LOGOS = {
    "РигаМолл": "img/sales_report/stores/riga_mall.jpg",
    "Рига Молл": "img/sales_report/stores/riga_mall.jpg",

    "Гарден Сити": "img/sales_report/stores/garden_logo.png",

    "Европарк": "img/sales_report/stores/europark.png",
    "Капитолий Вернадского": "img/sales_report/stores/capitol.jpg",
    "Фэшн Хаус": "img/sales_report/stores/fashion_house.png",
    "Ривер Хаус": "img/sales_report/stores/river_house.png",

    "Интернет-продажи": "img/sales_report/stores/e-commerce-store.png",
    "Интернет Магазин": "img/sales_report/stores/e-commerce-store.png",

    "Дизайнеры и архитекторы": "img/sales_report/stores/design.png",
    "Дизайнеры": "img/sales_report/stores/design.png",

    "Основной склад": "img/sales_report/stores/store.png",

    "Корпоративные продажи": "img/sales_report/stores/b2b.png",
    "B2B: Прочее": "img/sales_report/stores/b2b.png",
}


def _norm(s: str) -> str:
    return "".join((s or "").lower().split())


# делаем нормализованный индекс
_STORE_LOGOS_NORM = {_norm(k): v for k, v in STORE_LOGOS.items()}


def attach_store_logos(rows: list[dict]) -> list[dict]:
    for r in rows:
        name = (r.get("shop") or r.get("store") or "").strip()

        if not name or name in ("Прочие", "ИТОГО", "Итого", "—"):
            r["logo"] = None
            continue

        r["logo"] = _STORE_LOGOS_NORM.get(_norm(name))

    return rows

