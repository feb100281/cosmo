# # corporate/reports/assouline/parser.py
# import pandas as pd
# from io import BytesIO
# from dataclasses import dataclass
# from typing import List, Optional

# @dataclass
# class AssoulineBook:
#     isbn: str
#     title: str
#     collection: str
#     price_usd: float
#     price_eur: float
#     price_gbp: float
#     eu_stock: int
#     us_stock: int
#     emea_eta: Optional[str]
#     americas_eta: Optional[str]
#     notes: str
#     is_available_emea: bool
#     is_preorder: bool
    
# class AssoulineParser:
#     def __init__(self, file_content: bytes):
#         self.file_content = file_content
        
#     def parse(self) -> List[AssoulineBook]:
#         """Парсит Excel и возвращает список книг"""
        
#         # Читаем лист MASTER
#         df = pd.read_excel(
#             BytesIO(self.file_content), 
#             sheet_name='MASTER'
#         )
        
#         books = []
        
#         for _, row in df.iterrows():
#             # ISBN
#             isbn = str(row.get('ISBN', '')).strip()
#             if not isbn or isbn == 'nan' or len(isbn) < 10:
#                 continue
            
#             # Название
#             title = str(row.get('TITLES', ''))[:100]
#             if title == 'nan':
#                 title = ''
            
#             # Коллекция
#             collection = str(row.get('COLLECTION', ''))
#             if collection == 'nan':
#                 collection = ''
            
#             # Цены -
#             try:
#                 price_usd = float(row.get('USD ($)', 0)) if pd.notna(row.get('USD ($)')) else 0.0
#             except:
#                 price_usd = 0.0
                
#             try:
#                 price_eur = float(row.get('EUR (€)', 0)) if pd.notna(row.get('EUR (€)')) else 0.0
#             except:
#                 price_eur = 0.0
                
#             try:
#                 price_gbp = float(row.get('GBP (£)', 0)) if pd.notna(row.get('GBP (£)')) else 0.0
#             except:
#                 price_gbp = 0.0
            
#             # Остатки
#             try:
#                 eu_stock = int(row.get('EU stock (9)', 0)) if pd.notna(row.get('EU stock (9)')) else 0
#             except:
#                 eu_stock = 0
                
#             try:
#                 us_stock = int(row.get('US stock (9)', 0)) if pd.notna(row.get('US stock (9)')) else 0
#             except:
#                 us_stock = 0
            
#             # ETA
#             emea_eta_raw = row.get('EMEA')
#             emea_eta = str(emea_eta_raw) if pd.notna(emea_eta_raw) and str(emea_eta_raw) != 'nan' else None
            
#             americas_eta_raw = row.get('Americas & Caribbean')
#             americas_eta = str(americas_eta_raw) if pd.notna(americas_eta_raw) and str(americas_eta_raw) != 'nan' else None
            
#             # Notes
#             notes_raw = row.get('Notes')
#             notes = str(notes_raw) if pd.notna(notes_raw) and str(notes_raw) != 'nan' else ''
            
#             # Статус
#             is_available_emea = eu_stock > 0
#             is_preorder = bool(emea_eta and emea_eta not in ['', 'nan', 'None'])
            
#             # Пропускаем строки без цены
#             if price_usd == 0 and price_eur == 0 and price_gbp == 0:
#                 continue
            
#             book = AssoulineBook(
#                 isbn=isbn,
#                 title=title,
#                 collection=collection,
#                 price_usd=price_usd,
#                 price_eur=price_eur,
#                 price_gbp=price_gbp,
#                 eu_stock=eu_stock,
#                 us_stock=us_stock,
#                 emea_eta=emea_eta,
#                 americas_eta=americas_eta,
#                 notes=notes,
#                 is_available_emea=is_available_emea,
#                 is_preorder=is_preorder
#             )
#             books.append(book)
            
#         print(f"✅ Распарсено {len(books)} книг")
#         return books



import pandas as pd
from io import BytesIO
from dataclasses import dataclass
from typing import List, Optional

@dataclass
class AssoulineBook:
    isbn: str
    title: str
    collection: str
    price_usd: float
    price_eur: float
    price_gbp: float
    eu_stock: int
    us_stock: int
    emea_eta: Optional[str]
    americas_eta: Optional[str]
    notes: str
    is_available_emea: bool
    is_preorder: bool
    url: Optional[str] = None
    
class AssoulineParser:
    def __init__(self, file_content: bytes):
        self.file_content = file_content
        
    def parse(self) -> List[AssoulineBook]:
        """Парсит Excel и возвращает список книг"""
        
        # Выводим все листы в файле
        xl_file = pd.ExcelFile(BytesIO(self.file_content))
        print("=" * 50)
        print(f"📋 Найдено листов: {len(xl_file.sheet_names)}")
        for i, sheet in enumerate(xl_file.sheet_names):
            print(f"   {i+1}. {sheet}")
        print("=" * 50)
        
        # Пробуем прочитать MASTER
        try:
            df = pd.read_excel(
                BytesIO(self.file_content), 
                sheet_name='MASTER'
            )
            print("✅ Читаем лист: MASTER")
        except:
            df = pd.read_excel(
                BytesIO(self.file_content), 
                sheet_name=xl_file.sheet_names[0]
            )
            print(f"✅ MASTER не найден, читаем первый лист: {xl_file.sheet_names[0]}")
        
        # Выводим все названия колонок
        print("\n📊 Названия колонок в листе:")
        for col in df.columns:
            print(f"   - {col}")
        print("=" * 50)
        
        # Ищем ссылки во всех колонках
        print("\n🔍 Поиск ссылок во всех колонках:")
        found_links = False
        for col in df.columns:
            for idx in range(min(5, len(df))):
                val = str(df.iloc[idx].get(col, ''))
                if 'http' in val or 'www.' in val or '.com' in val or 'assouline' in val.lower():
                    print(f"✅ Найдена ссылка в колонке '{col}': {val[:100]}")
                    found_links = True
                    break
            if found_links:
                break
        if not found_links:
            print("❌ Ссылки не найдены ни в одной колонке")
        print("=" * 50)
        
        books = []
        
        for _, row in df.iterrows():
            # ISBN
            isbn = str(row.get('ISBN', '')).strip()
            if not isbn or isbn == 'nan' or len(isbn) < 10:
                continue
            
            # Название (очищаем от HTML тегов, если есть)
            title_raw = str(row.get('TITLES', ''))
            if title_raw == 'nan':
                title = ''
            else:
                # Удаляем HTML теги, если есть
                import re
                title = re.sub(r'<[^>]+>', '', title_raw)[:100]
            
            # Коллекция
            collection = str(row.get('COLLECTION', ''))
            if collection == 'nan':
                collection = ''
            
            # Цены
            try:
                price_usd = float(row.get('USD ($)', 0)) if pd.notna(row.get('USD ($)')) else 0.0
            except:
                price_usd = 0.0
                
            try:
                price_eur = float(row.get('EUR (€)', 0)) if pd.notna(row.get('EUR (€)')) else 0.0
            except:
                price_eur = 0.0
                
            try:
                price_gbp = float(row.get('GBP (£)', 0)) if pd.notna(row.get('GBP (£)')) else 0.0
            except:
                price_gbp = 0.0
            
            # Остатки
            try:
                eu_stock = int(row.get('EU stock (9)', 0)) if pd.notna(row.get('EU stock (9)')) else 0
            except:
                eu_stock = 0
                
            try:
                us_stock = int(row.get('US stock (9)', 0)) if pd.notna(row.get('US stock (9)')) else 0
            except:
                us_stock = 0
            
            # ETA
            emea_eta_raw = row.get('EMEA')
            emea_eta = str(emea_eta_raw) if pd.notna(emea_eta_raw) and str(emea_eta_raw) != 'nan' else None
            
            americas_eta_raw = row.get('Americas & Caribbean')
            americas_eta = str(americas_eta_raw) if pd.notna(americas_eta_raw) and str(americas_eta_raw) != 'nan' else None
            
            # Notes
            notes_raw = row.get('Notes')
            notes = str(notes_raw) if pd.notna(notes_raw) and str(notes_raw) != 'nan' else ''
            
            # ПОИСК ССЫЛКИ во всех колонках этой строки
            url = None
            for col in df.columns:
                val = row.get(col)
                if pd.notna(val) and isinstance(val, str):
                    if 'http' in val or 'www.' in val:
                        url = val
                        break
                    # Также ищем ссылки в формате HTML
                    if 'href=' in val:
                        import re
                        match = re.search(r'href=[\'"]?([^\'" >]+)', val)
                        if match:
                            url = match.group(1)
                            break
            
            # Если не нашли ссылку, пробуем сгенерировать по ISBN
            if not url and isbn:
                url = f"https://www.assouline.com/products/{isbn}"
            
            # Статус
            is_available_emea = eu_stock > 0
            is_preorder = bool(emea_eta and emea_eta not in ['', 'nan', 'None'])
            
            # Пропускаем строки без цены
            if price_usd == 0 and price_eur == 0 and price_gbp == 0:
                continue
            
            book = AssoulineBook(
                isbn=isbn,
                title=title,
                collection=collection,
                price_usd=price_usd,
                price_eur=price_eur,
                price_gbp=price_gbp,
                eu_stock=eu_stock,
                us_stock=us_stock,
                emea_eta=emea_eta,
                americas_eta=americas_eta,
                notes=notes,
                is_available_emea=is_available_emea,
                is_preorder=is_preorder,
                url=url
            )
            books.append(book)
            
        print(f"✅ Распарсено {len(books)} книг")
        books_with_url = sum(1 for b in books if b.url)
        print(f"🔗 Книг со ссылками: {books_with_url} ({(books_with_url/len(books)*100):.1f}%)")
        if books_with_url == 0:
            print("💡 Ссылки не найдены. Будет использована генерация по ISBN")
        print("=" * 50)
        return books