# corporate/reports/excel_report/workbook.py
from io import BytesIO
from openpyxl import Workbook
from datetime import datetime


from .dataset import (
    get_years,
    get_overview_metrics,
    # get_manufacturers_yearly,
    get_categories_yearly,
    get_root_categories_yearly,
    get_manufacturer_category_matrix,
    get_top_items,
    get_manufacturer_item_counts,
    get_manufacturer_share_by_year,
    # get_manufacturer_category_dependence,
    get_category_totals,
    # get_lost_categories,
    get_top_growth_manufacturers,
    get_new_vs_old_manufacturers,
    get_store_x_manufacturer,
    get_overview_store_details,
    get_manufacturers_yoy_yearly,
    get_manufacturer_categories_yoy_yearly,
    get_anti_top_manufacturers, 
    get_anti_top_categories,
    get_top_growth_categories,
    get_categories_yoy_yearly,
    get_root_categories_yoy_yearly,
    get_category_manufacturer_dependence,
    get_manufacturer_category_item_counts,
    get_top_items_qty_by_year
)
from .sheets.sheet_overview import build_overview_sheet
# from .sheets.sheet_manufacturers import build_manufacturers_sheet
from .sheets.sheet_categories import build_categories_sheet
from .sheets.sheet_matrix import build_matrix_sheet
from .sheets.sheet_root_categories import build_root_categories_sheet
from .sheets.sheet_top_items import build_top_items_sheet
from .sheets.sheet_yoy import build_yoy_sheet
from .sheets.sheet_anti_top import build_anti_top_sheet
from .sheets.sheet_share import build_share_sheet
from .sheets.sheet_category_dependence import build_category_dependence_sheet
from .sheets.sheet_assortment_vs_revenue import build_assortment_vs_revenue_sheet
from .sheets.sheet_abc_manufacturers import build_abc_manufacturers_sheet
from .sheets.sheet_abc_categories import build_abc_categories_sheet
from .sheets.sheet_lost_categories import build_lost_categories_sheet
from .sheets.sheet_top_growth import build_top_growth_sheet
from .sheets.sheet_new_vs_old import build_new_vs_old_sheet
from .sheets.sheet_store_x_manufacturer import build_store_x_manufacturer_sheet
from .sheets.sheet_index import build_index_sheet





def build_manufacturers_excel_report(start_year: int = 2022, manufacturer_ids: list[int] | None = None) -> BytesIO:
    manufacturer_ids = manufacturer_ids or []

    years = get_years(start_year=start_year)
    overview_rows = get_overview_metrics(start_year=start_year, manufacturer_ids=manufacturer_ids)
    overview_store_rows = get_overview_store_details(start_year=start_year,manufacturer_ids=manufacturer_ids,)
    manufacturer_rows = get_manufacturers_yoy_yearly(start_year=start_year, manufacturer_ids=manufacturer_ids)
    category_rows = get_categories_yearly(start_year=start_year, manufacturer_ids=manufacturer_ids)
    root_rows = get_root_categories_yearly(start_year=start_year, manufacturer_ids=manufacturer_ids)
    matrix_rows = get_manufacturer_category_matrix(start_year=start_year, manufacturer_ids=manufacturer_ids)
    top_items_rows = get_top_items(start_year=start_year, manufacturer_ids=manufacturer_ids, limit=300)

    manufacturer_item_counts = get_manufacturer_item_counts(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    manufacturer_share_rows = get_manufacturer_share_by_year(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    # category_dependence_rows = get_manufacturer_category_dependence(
    #     start_year=start_year,
    #     manufacturer_ids=manufacturer_ids,
    # )
    category_totals = get_category_totals(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    
    
    # lost_categories_rows = get_lost_categories(
    #     start_year=start_year,
    #     manufacturer_ids=manufacturer_ids,
    # )

    new_vs_old_rows = get_new_vs_old_manufacturers(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    store_x_manufacturer_rows = get_store_x_manufacturer(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    wb = Workbook()
    default_ws = wb.active
    wb.remove(default_ws)
    build_index_sheet(wb, generated_at=datetime.now())
    


    build_overview_sheet(wb, overview_rows, overview_store_rows)
    
    # build_manufacturers_sheet(wb, years, manufacturer_rows)
    manufacturer_rows = get_manufacturers_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )

    category_rows = get_manufacturer_categories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    build_yoy_sheet(wb, years, manufacturer_rows, category_rows)
    

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

    build_anti_top_sheet(wb, anti_top_data, anti_top_categories_data)
    
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

    build_top_growth_sheet(
        wb,
        top_growth_data=top_growth_data,
        top_growth_categories_data=top_growth_categories_data,
    )
    
    
    
    
    build_share_sheet(wb, years, manufacturer_share_rows)

    category_rows = get_categories_yoy_yearly(
        start_year=start_year,
        manufacturer_ids=manufacturer_ids,
    )
    build_categories_sheet(wb, years, category_rows)
    
    
    root_category_rows = get_root_categories_yoy_yearly(
    start_year=start_year,
    manufacturer_ids=manufacturer_ids,
    )

    build_root_categories_sheet(wb, years, root_category_rows)
    
    

    category_dependence_rows = get_category_manufacturer_dependence(
    start_year=start_year,
    manufacturer_ids=manufacturer_ids,
    )
    build_category_dependence_sheet(wb, category_dependence_rows)

    build_matrix_sheet(wb, matrix_rows)
    manufacturer_rows = get_manufacturer_item_counts(start_year, manufacturer_ids)
    category_rows = get_manufacturer_category_item_counts(start_year, manufacturer_ids)

    build_assortment_vs_revenue_sheet(
        wb,
        manufacturer_rows=manufacturer_rows,
        category_rows=category_rows,
    )
    build_abc_manufacturers_sheet(wb, manufacturer_item_counts)
    build_abc_categories_sheet(wb, category_totals)
    # build_lost_categories_sheet(wb, lost_categories_rows)

    # build_new_vs_old_sheet(wb, new_vs_old_rows)
    build_store_x_manufacturer_sheet(wb, store_x_manufacturer_rows)
    # build_top_items_sheet(wb, top_items_rows)
    
    
    
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

    build_top_items_sheet(
        wb,
        rows=top_items_rows,
        qty_by_year_rows=top_items_qty_by_year_rows,
    )
    
    
    
    
    sheet_name_map = {
            "Сводка": "1",
            # "Производители": "2",
            "YOY analysis": "2",
            "Anti-top manufacturers": "3",
            "Top growth manufacturers": "4",
            "Manufacturer share": "5",
            "Categories": "6",
            # "Lost categories": "8",
            "Root Categories": "7",
            "Category dependence": "8",
            "Matrix MF x Cat": "9",
            "Assortment vs revenue": "10",
            "ABC manufacturers": "11",
            "ABC categories": "12",
            # "New vs old manufacturers": "15",
            "Store x manufacturer": "13",
            "Top Items": "14",
        }
    


    for ws in wb.worksheets:
        if ws.title in sheet_name_map:
            ws.title = sheet_name_map[ws.title]


        
        

    for ws in wb.worksheets:
        ws.sheet_view.showGridLines = False
        ws.auto_filter.ref = None

    bio = BytesIO()
    wb.save(bio)
    bio.seek(0)
    return bio