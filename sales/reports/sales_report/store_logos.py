# store_logos.py
# ключ — ровно как приходит r["store"] (название магазина)
# значение — путь ОТНОСИТЕЛЬНО /static/
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



def attach_store_logos(store_rows: list[dict]) -> list[dict]:
    for r in store_rows:
        name = r.get("store")
        # для ИТОГО логотип не нужен
        r["logo"] = STORE_LOGOS.get(name)
    return store_rows
