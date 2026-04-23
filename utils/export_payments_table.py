#!/usr/bin/env python
"""
Скрипт для выгрузки ВСЕХ сырых данных из таблицы оплат
Запуск: python -m utils.export_payments_table
"""

import os
import sys
import csv
from datetime import datetime

# Добавляем путь к проекту
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'fr.settings')
import django
django.setup()

from orders.models import OrdersCF


def save_all_data_to_csv():
    """Сохраняет ВСЕ данные из OrdersCF в CSV"""
    
    print("=" * 50)
    print("Выгрузка сырых данных из OrdersCF")
    print("=" * 50)
    
    # Создаем папку для экспорта
    export_dir = os.path.join(os.path.dirname(__file__), 'exports')
    os.makedirs(export_dir, exist_ok=True)
    
    # Имя файла
    filename = f"orderscf_raw_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    filepath = os.path.join(export_dir, filename)
    
    print(f"\n📊 Получаем данные из таблицы OrdersCF...")
    
    # Получаем ВСЕ записи
    queryset = OrdersCF.objects.all()
    total_count = queryset.count()
    
    print(f"✅ Найдено записей: {total_count}")
    
    if total_count == 0:
        print("❌ Нет данных для экспорта")
        return
    
    print(f"\n💾 Сохраняем в файл: {filepath}")
    
    # Получаем ТОЛЬКО поля без связей (чтобы не было ошибок)
    fields = []
    for field in OrdersCF._meta.get_fields():
        # Пропускаем связанные поля (ForeignKey, OneToOne, ManyToMany)
        if field.is_relation:
            continue
        fields.append(field.name)
    
    print(f"📋 Экспортируем колонки: {len(fields)} (только простые поля)")
    
    # Записываем CSV
    with open(filepath, 'w', encoding='utf-8-sig', newline='') as csvfile:
        writer = csv.DictWriter(
            csvfile, 
            fieldnames=fields,
            delimiter='|',
            quoting=csv.QUOTE_MINIMAL,
            escapechar='\\'
        )
        
        writer.writeheader()
        
        # Записываем данные порциями
        batch_size = 1000
        processed = 0
        
        for i in range(0, total_count, batch_size):
            batch = list(queryset[i:i+batch_size])
            
            for obj in batch:
                row = {}
                for field in fields:
                    value = getattr(obj, field)
                    
                    if value is None:
                        value = ''
                    elif isinstance(value, datetime):
                        value = value.strftime('%Y-%m-%d %H:%M:%S')
                    elif isinstance(value, (int, float)):
                        value = str(value)
                    elif isinstance(value, str):
                        value = value.replace('\n', ' ').replace('\r', ' ').replace('|', '\\|')
                    
                    row[field] = value
                
                writer.writerow(row)
                processed += 1
                
                if processed % 1000 == 0:
                    print(f"   Обработано: {processed} / {total_count}")
    
    print(f"\n✅ Готово!")
    print(f"📁 Файл: {filepath}")
    print(f"📊 Записей: {total_count}")
    print(f"📋 Колонок: {len(fields)}")
    print("=" * 50)
    
    return filepath


if __name__ == "__main__":
    save_all_data_to_csv()