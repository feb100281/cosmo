# corporate/reports/assouline/views.py
from django.shortcuts import render, redirect
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from datetime import datetime
import json

from .forms import AssoulineCatalogForm
from .parser import AssoulineParser
from .analyzer import AssoulineAnalyzer
from .excel_export import export_assouline_to_excel


def assouline_analyze_view(request):
    """View для анализа каталога Assouline"""
    
    if request.method == 'POST':
        form = AssoulineCatalogForm(request.POST, request.FILES)
        if form.is_valid():
            catalog_file = request.FILES['catalog_file']
            region = form.cleaned_data['region']
            start_year = form.cleaned_data['start_year']
            
            try:
                # Парсим файл
                parser = AssoulineParser(catalog_file.read())
                books = parser.parse()
                
                # Анализируем продажи
                analyzer = AssoulineAnalyzer(books, start_year)
                analyzer.fetch_sales_from_db()
                recommendations = analyzer.calculate_recommendations()
                collections = analyzer.get_collections_analysis()
                
                # ============================================================
                # ДОБАВЛЯЕМ URL В КАЖДУЮ РЕКОМЕНДАЦИЮ
                # ============================================================
                url_by_isbn = {book.isbn: book.url for book in books if book.url}
                
                for rec in recommendations:
                    isbn = rec.get('isbn')
                    if isbn:
                        if isbn in url_by_isbn:
                            rec['url'] = url_by_isbn[isbn]
                        else:
                            # Генерируем ссылку по ISBN
                            rec['url'] = f"https://www.assouline.com/products/{isbn}"
                    else:
                        rec['url'] = None
                
                # Сохраняем в сессию
                request.session['assouline_recommendations'] = recommendations
                request.session['assouline_region'] = region
                
                # Подсчет статистики
                total_books = len(books)
                available_now = len([b for b in books if b.is_available_emea])
                preorders_count = len([b for b in books if b.is_preorder])
                
                # Расчет бюджета
                total_cost_usd = sum(r.get('estimated_cost_usd', 0) for r in recommendations)
                total_budget_rub = total_cost_usd * 90
                
                context = {
                    'title': 'Анализ каталога ASSOULINE',
                    'generated_at': datetime.now(),
                    'total_books': total_books,
                    'available_now': available_now,
                    'preorders_count': preorders_count,
                    'total_budget': total_budget_rub,
                    'total_budget_usd': total_cost_usd,
                    'budget_percent': 100,
                    'top_recommendations': recommendations[:],
                    'collections': collections,
                    'region': region,
                }
                
                return render(request, 'admin/corporate/assouline_report.html', context)
                
            except Exception as e:
                messages.error(request, f'Ошибка при анализе: {str(e)}')
                import traceback
                traceback.print_exc()
        else:
            messages.error(request, 'Пожалуйста, заполните форму корректно')
    else:
        form = AssoulineCatalogForm()
    
    context = {
        'title': 'Анализ каталога ASSOULINE',
        'form': form,
    }
    return render(request, 'admin/corporate/manufacturer/assouline_upload.html', context)

def assouline_export_excel_view(request):
    """Экспорт рекомендаций в Excel"""
    
    recommendations = request.session.get('assouline_recommendations', [])
    region = request.session.get('assouline_region', 'EMEA')
    
    if not recommendations:
        messages.error(request, 'Нет данных для экспорта. Сначала выполните анализ.')
        return redirect('assouline:analyze')
    
    return export_assouline_to_excel(recommendations, region)


def assouline_optimize_by_budget_view(request):
    """Оптимизация заказа под заданный бюджет"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        target_budget_usd = float(data.get('budget_usd', 0))
        
        recommendations = request.session.get('assouline_recommendations', [])
        if not recommendations:
            return JsonResponse({'error': 'Нет данных для пересчета'}, status=400)
        
        # Сортируем по приоритету
        sorted_recs = sorted(recommendations, key=lambda x: (-x.get('priority', 0), -x.get('qty_sold', 0)))
        
        # Коэффициенты сокращения
        reduction_factors = {
            5: 1.0,   # MUST HAVE
            4: 0.7,   # HIGH
            3: 0.4,   # MEDIUM
            2: 0.2,   # TEST
            1: 0.0,   # LOW
            0: 0.0,
        }
        
        # ВАЖНО: создаем НОВЫЙ список, а не добавляем к старому
        adjusted_recs = []
        total_cost = 0
        
        for rec in sorted_recs:
            # Создаем копию словаря, чтобы не мутировать оригинал
            new_rec = rec.copy()
            original_qty = new_rec.get('recommended_qty', 0)
            priority = new_rec.get('priority', 0)
            price = new_rec.get('price_usd', 0)
            
            if original_qty == 0 or priority <= 1:
                adjusted_qty = 0
            else:
                factor = reduction_factors.get(priority, 0.2)
                adjusted_qty = max(1, int(original_qty * factor)) if factor > 0 else 0
            
            estimated = price * adjusted_qty
            
            if total_cost + estimated > target_budget_usd and adjusted_qty > 1:
                if price <= (target_budget_usd - total_cost):
                    adjusted_qty = 1
                    estimated = price
                else:
                    adjusted_qty = 0
                    estimated = 0
            
            if adjusted_qty > 0 and total_cost + estimated <= target_budget_usd:
                total_cost += estimated
                new_rec['recommended_qty'] = adjusted_qty
                new_rec['estimated_cost_usd'] = estimated
            else:
                new_rec['recommended_qty'] = 0
                new_rec['estimated_cost_usd'] = 0
            
            # Добавляем ТОЛЬКО один раз
            adjusted_recs.append(new_rec)
        
        # Полностью ЗАМЕНЯЕМ список в сессии
        request.session['assouline_recommendations'] = adjusted_recs
        
        return JsonResponse({
            'status': 'ok',
            'total_cost': total_cost,
            'recommendations': [{
                'isbn': r.get('isbn'),
                'recommended_qty': r.get('recommended_qty', 0)
            } for r in adjusted_recs if r.get('recommended_qty', 0) > 0]
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'error': str(e)}, status=500)

def assouline_update_order_view(request):
    """Обновление заказа вручную"""
    
    if request.method != 'POST':
        return JsonResponse({'error': 'Method not allowed'}, status=405)
    
    try:
        data = json.loads(request.body)
        updates = data.get('updates', [])
        
        recommendations = request.session.get('assouline_recommendations', [])
        if not recommendations:
            return JsonResponse({'error': 'Нет данных'}, status=400)
        
        rec_by_isbn = {r.get('isbn'): r for r in recommendations}
        
        for update in updates:
            isbn = update.get('isbn')
            qty = update.get('qty', 0)
            
            if isbn in rec_by_isbn:
                rec_by_isbn[isbn]['recommended_qty'] = qty
                rec_by_isbn[isbn]['estimated_cost_usd'] = rec_by_isbn[isbn]['price_usd'] * qty
        
        updated_recs = list(rec_by_isbn.values())
        request.session['assouline_recommendations'] = updated_recs
        
        return JsonResponse({'status': 'ok', 'updated': len(updates)})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)