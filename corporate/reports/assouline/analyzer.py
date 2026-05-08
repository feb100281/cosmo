from typing import List, Dict
from django.db import connection
from .parser import AssoulineBook

class AssoulineAnalyzer:
    def __init__(self, books: List[AssoulineBook], start_year: int = 2022):
        self.books = books
        self.start_year = start_year
        self.sales_data = {}
        
    def fetch_sales_from_db(self):
        """Загружает данные о продажах из базы"""
        
        # Собираем ISBN
        isbns = []
        for book in self.books:
            if book.isbn and len(book.isbn) >= 10:
                isbns.append(book.isbn)
        
        if not isbns:
            return
            
        isbns = list(set(isbns))
        
        # Разбиваем на части по 500 ISBN (чтобы не было слишком длинного запроса)
        chunk_size = 500
        all_sales = {}
        
        for i in range(0, len(isbns), chunk_size):
            chunk = isbns[i:i+chunk_size]
            placeholders = ','.join(['%s'] * len(chunk))
            
            query = f"""
                SELECT 
                    it.article as isbn,
                    COALESCE(SUM(s.quant_dt - s.quant_cr), 0) as qty_sold,
                    COALESCE(SUM(s.dt - s.cr), 0) as revenue
                FROM sales_salesdata s
                JOIN corporate_items it ON it.id = s.item_id
                WHERE it.article IN ({placeholders})
                    AND YEAR(s.date) >= %s
                GROUP BY it.article
            """
            
            params = chunk + [self.start_year]
            
            with connection.cursor() as cursor:
                cursor.execute(query, params)
                rows = cursor.fetchall()
                
            for row in rows:
                isbn, qty, revenue = row
                all_sales[isbn] = {
                    'qty_sold': int(qty) if qty else 0,
                    'revenue': float(revenue) if revenue else 0.0
                }
        
        self.sales_data = all_sales
        print(f"✅ Найдено продаж для {len(self.sales_data)} ISBN")
    
    def calculate_recommendations(self) -> List[Dict]:
        """Рассчитывает рекомендации по заказу"""
        
        recommendations = []
        
        for book in self.books:
            # Пропускаем книги без цены
            if book.price_usd == 0 and book.price_eur == 0:
                continue
            
            # Получаем данные о продажах
            sales = self.sales_data.get(book.isbn, {'qty_sold': 0, 'revenue': 0.0})
            qty_sold = sales['qty_sold']
            
            # ===== ЛОГИКА РАСЧЕТА РЕКОМЕНДУЕМОГО КОЛИЧЕСТВА =====
            recommended_qty = 0
            
            # 1. Хиты продаж (более 10 шт в год)
            if qty_sold >= 10:
                recommended_qty = int(qty_sold * 0.7)  # 70% от продаж
                if recommended_qty < 3:
                    recommended_qty = 3  # минимум 3 штуки для хитов
                    
            # 2. Средние продажи (5-9 шт)
            elif qty_sold >= 5:
                recommended_qty = int(qty_sold * 0.5)  # 50% от продаж
                if recommended_qty < 2:
                    recommended_qty = 2
                    
            # 3. Низкие продажи (1-4 шт)
            elif qty_sold >= 1:
                recommended_qty = qty_sold  # столько же
                
            # 4. Новинки (Spring 2026 или пометка New)
            elif 'Spring 2026' in book.notes or 'New' in book.notes:
                recommended_qty = 2  # пробная партия
                
            # 5. Предзаказы (есть ETA)
            elif book.is_preorder:
                recommended_qty = 1  # минимальный тест
            
            # Корректируем с учетом остатков на складе поставщика
            if recommended_qty > book.eu_stock and book.eu_stock > 0:
                recommended_qty = book.eu_stock  # не можем заказать больше, чем есть
            elif book.eu_stock == 0 and recommended_qty > 0:
                # Если нет на складе EU, но есть в US - отмечаем как "под заказ"
                if book.us_stock > 0:
                    recommended_qty = min(recommended_qty, book.us_stock)
            
            # Рассчитываем сумму заказа
            estimated_cost = book.price_usd * recommended_qty
            
            # Определяем приоритет (для сортировки)
            priority = self._get_priority(qty_sold, book.is_preorder, book.notes)
            
            recommendations.append({
                'isbn': book.isbn,
                'title': book.title,
                'collection': book.collection,
                'price_usd': float(book.price_usd),
                'price_eur': float(book.price_eur),
                'qty_sold': qty_sold,
                'revenue': float(sales['revenue']),
                'eu_stock': book.eu_stock,
                'us_stock': book.us_stock,
                'status': self._get_status(book),
                'eta': book.emea_eta if book.is_preorder else None,
                'recommended_qty': recommended_qty,
                'estimated_cost_usd': estimated_cost,
                'priority': priority,
                'notes': book.notes,
                'url': book.url,  # ← ДОБАВЛЕНО поле url
            })
        
        # Сортируем по приоритету (от большего к меньшему) и по продажам
        recommendations.sort(key=lambda x: (-x['priority'], -x['qty_sold']))
        
        return recommendations
    
    def _get_status(self, book: AssoulineBook) -> str:
        """Определяет статус доступности"""
        if book.eu_stock > 0:
            return 'IN_STOCK'
        elif book.is_preorder:
            return 'PREORDER'
        elif book.us_stock > 0:
            return 'FROM_US'
        else:
            return 'OUT_OF_STOCK'
    
    def _get_priority(self, qty_sold: int, is_preorder: bool, notes: str) -> int:
        """Приоритет закупки (5 - highest, 0 - lowest)"""
        if qty_sold >= 10:
            return 5  # MUST HAVE
        elif qty_sold >= 5:
            return 4  # HIGH
        elif qty_sold >= 1:
            return 3  # MEDIUM
        elif 'Spring 2026' in notes or 'New' in notes:
            return 2  # TEST (новинки)
        elif is_preorder:
            return 1  # LOW (просто предзаказ)
        else:
            return 0  # SKIP
    
    def get_collections_analysis(self) -> Dict:
        """Анализ коллекций"""
        collections = {}
        
        for book in self.books:
            if not book.collection:
                continue
            
            if book.collection not in collections:
                collections[book.collection] = {
                    'total_books': 0,
                    'available_books': 0,
                    'preorder_books': 0,
                    'total_sold': 0,
                    'total_revenue': 0.0,
                    'avg_price': 0.0
                }
            
            collections[book.collection]['total_books'] += 1
            if book.eu_stock > 0:
                collections[book.collection]['available_books'] += 1
            if book.is_preorder:
                collections[book.collection]['preorder_books'] += 1
                
            sales = self.sales_data.get(book.isbn, {'qty_sold': 0, 'revenue': 0.0})
            collections[book.collection]['total_sold'] += sales['qty_sold']
            collections[book.collection]['total_revenue'] += float(sales['revenue'])
        
        # Считаем средние цены
        for coll in collections:
            if collections[coll]['total_books'] > 0:
                # Приблизительная средняя цена (можно уточнить)
                collections[coll]['avg_price'] = 0
        
        return collections