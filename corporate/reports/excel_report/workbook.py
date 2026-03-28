# corporate/reports/excel_report/workbook.py

from io import BytesIO
from datetime import datetime

from openpyxl import Workbook

from .dataset import (
    get_years,
    get_overview_metrics,
    get_overview_store_details,
    get_manufacturers_yoy_yearly,
    get_manufacturer_categories_yoy_yearly,
    get_anti_top_manufacturers,
    get_anti_top_categories,
    get_top_growth_manufacturers,
    get_top_growth_categories,
    get_manufacturer_share_by_year,
    get_categories_yoy_yearly,
    get_subcategories_yoy_yearly,
    get_root_categories_yoy_yearly,
    get_category_manufacturer_dependence,
    get_manufacturer_category_matrix,
    get_assortment_width_by_manufacturer,
    get_assortment_width_by_subcategory,
    get_new_lost_sku_by_manufacturer,
    get_new_lost_sku_by_manufacturer_subcategory,
    get_manufacturer_item_counts,
    get_manufacturer_category_item_counts,
    get_category_totals,
    get_store_x_manufacturer,
    get_top_items,
    get_top_items_qty_by_year,
    get_subcategory_manufacturer_dependence,
    get_sku_productivity_by_subcategory,
    get_price_segment_subcategory_yoy
    
)

from .sheets.sheet_index import build_index_sheet
from .sheets.sheet_overview import build_overview_sheet
from .sheets.sheet_yoy import build_yoy_sheet
from .sheets.sheet_anti_top import build_anti_top_sheet
from .sheets.sheet_top_growth import build_top_growth_sheet
from .sheets.sheet_share import build_share_sheet
from .sheets.sheet_categories import build_categories_sheet
from .sheets.sheet_subcategories import build_subcategories_sheet
from .sheets.sheet_root_categories import build_root_categories_sheet
from .sheets.sheet_subcategory_dependence import build_subcategory_dependence_sheet
from .sheets.sheet_matrix import build_matrix_sheet
from .sheets.sheet_assortment_width import build_assortment_width_sheet
from .sheets.sheet_assortment_width_subcategories import build_assortment_width_subcategories_sheet
from .sheets.sheet_sku_productivity import build_sku_productivity_sheet
from .sheets.sheet_new_lost_sku import build_new_lost_sku_sheet
from .sheets.sheet_price_segmentation import build_price_segmentation_sheet
from .sheets.sheet_assortment_vs_revenue import build_assortment_vs_revenue_sheet
from .sheets.sheet_abc_manufacturers import build_abc_manufacturers_sheet
from .sheets.sheet_abc_categories import build_abc_categories_sheet
from .sheets.sheet_store_x_manufacturer import build_store_x_manufacturer_sheet
from .sheets.sheet_top_items import build_top_items_sheet


def build_manufacturers_excel_report(
    start_year: int = 2022,
    manufacturer_ids: list[int] | None = None,
) -> BytesIO:
    manufacturer_ids = manufacturer_ids or []

    # -----------------------------
    # Загружаем все нужные данные
    # -----------------------------
    years = get_years(start_year=start_year)

    overview_rows = get_overview_metrics(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    overview_store_rows = get_overview_store_details(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    yoy_manufacturer_rows = get_manufacturers_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    yoy_manufacturer_category_rows = get_manufacturer_categories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    anti_top_data = get_anti_top_manufacturers(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        limit=20,
    )
    anti_top_manufacturer_names = [r["manufacturer"] for r in anti_top_data["rows"]]
    anti_top_categories_data = get_anti_top_categories(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        anti_top_manufacturers=anti_top_manufacturer_names,
    )

    top_growth_data = get_top_growth_manufacturers(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        limit=20,
    )
    top_growth_categories_data = get_top_growth_categories(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        top_growth_manufacturers=[r["manufacturer"] for r in top_growth_data["rows"]],
    )

    manufacturer_share_rows = get_manufacturer_share_by_year(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    categories_yoy_rows = get_categories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    subcategories_yoy_rows = get_subcategories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    root_categories_yoy_rows = get_root_categories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    category_dependence_rows = get_category_manufacturer_dependence(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    matrix_rows = get_manufacturer_category_matrix(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    assortment_width_rows = get_assortment_width_by_manufacturer(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    assortment_width_subcategory_rows = get_assortment_width_by_subcategory(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    
    sku_productivity_rows = get_sku_productivity_by_subcategory(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    new_lost_summary = get_new_lost_sku_by_manufacturer(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    new_lost_subcategories = get_new_lost_sku_by_manufacturer_subcategory(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    
    price_segmentation_rows = get_price_segment_subcategory_yoy(
    start_year=start_year,
    manufacturer_ids=manufacturer_ids,
)


    manufacturer_item_counts = get_manufacturer_item_counts(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    manufacturer_category_item_counts = get_manufacturer_category_item_counts(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    category_totals = get_category_totals(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    store_x_manufacturer_rows = get_store_x_manufacturer(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    top_items_rows = get_top_items(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        limit=100,
    )
    top_items_qty_by_year_rows = get_top_items_qty_by_year(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
        limit=100,
    )

    # -----------------------------
    # Создаем workbook
    # -----------------------------
    wb = Workbook()
    default_ws = wb.active
    wb.remove(default_ws)

    build_index_sheet(wb, generated_at=datetime.now())

    # -----------------------------
    # Строим листы
    # -----------------------------
    build_overview_sheet(wb, overview_rows, overview_store_rows)

    build_yoy_sheet(
        wb,
        years,
        yoy_manufacturer_rows,
        yoy_manufacturer_category_rows,
    )

    build_anti_top_sheet(
        wb,
        anti_top_data,
        anti_top_categories_data,
    )

    build_top_growth_sheet(
        wb,
        top_growth_data=top_growth_data,
        top_growth_categories_data=top_growth_categories_data,
    )

    build_share_sheet(wb, years, manufacturer_share_rows)
    build_categories_sheet(wb, years, categories_yoy_rows)
    build_subcategories_sheet(wb, years, subcategories_yoy_rows)
    build_root_categories_sheet(wb, years, root_categories_yoy_rows)
    
    rows = get_subcategory_manufacturer_dependence(
    start_year=start_year,
    manufacturer_ids=manufacturer_ids,
    )
    build_subcategory_dependence_sheet(wb, rows)

    # build_subcategory_dependence_sheet(wb, category_dependence_rows)
    build_matrix_sheet(wb, matrix_rows)
    build_assortment_width_sheet(wb, years, assortment_width_rows)
    build_assortment_width_subcategories_sheet(wb, years, assortment_width_subcategory_rows)
    
    build_sku_productivity_sheet(wb, sku_productivity_rows)

    build_new_lost_sku_sheet(
        wb,
        summary_data=new_lost_summary,
        subcategory_data=new_lost_subcategories,
    )
    
    build_price_segmentation_sheet(wb, price_segmentation_rows)
    

 


    build_assortment_vs_revenue_sheet(
        wb,
        manufacturer_rows=manufacturer_item_counts,
        category_rows=manufacturer_category_item_counts,
    )

    build_abc_manufacturers_sheet(wb, manufacturer_item_counts)
    build_abc_categories_sheet(wb, category_totals)
    build_store_x_manufacturer_sheet(wb, store_x_manufacturer_rows)

    build_top_items_sheet(
        wb,
        rows=top_items_rows,
        qty_by_year_rows=top_items_qty_by_year_rows,
    )

    # -----------------------------
    # Переименование листов
    # -----------------------------
    sheet_name_map = {
        "Сводка": "1",
        "YOY analysis": "2",
        "Anti-top manufacturers": "3",
        "Top growth manufacturers": "4",
        "Manufacturer share": "5",
        "Categories": "6",
        "Subcategories": "7",
        "Root Categories": "8",
        "Subcategory dependence": "9",
        "Matrix MF x Cat": "10",
        "Ширина ассортимента": "11",
        "Ширина SKU по подкатегориям": "12",
        "SKU productivity": "13",
        "New vs Lost SKU": "14",
        "Price segmentation": "15",
        "Assortment vs revenue": "16",
        "ABC manufacturers": "17",
        "ABC categories": "18",
        "Store x manufacturer": "19",
        "Top Items": "20",

    }

    for ws in wb.worksheets:
        if ws.title in sheet_name_map:
            ws.title = sheet_name_map[ws.title]

    # -----------------------------
    # Общие настройки
    # -----------------------------
    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.auto_filter.ref = None

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio