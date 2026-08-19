# Интеграция COSMORELAX Daily Brief (newspaper) в основной проект

Этот модуль разработан и проверен в отдельной рабочей папке. Он **не изменяет**
`sales/reports/sales_plan_report/` и не содержит его копий — только импортирует
из него готовую бизнес-логику план/факта по кэшу (`get_sales_plan_data`).

После того как вы скопируете папку `newspaper/` в
`sales/reports/newspaper/`, нужно выполнить шаги ниже.

## 0. Куда что кладём — коротко

**Важно:** в этом проекте `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`
(проверено в `fr/settings.py`) — то есть корень шаблонов для Django это
**`<project_root>/templates/`**, а не `sales/templates/`. Именно поэтому у
старого отчёта `full_report.html` физически лежит в
`templates/reports/sales_plan_report/full_report.html` (в корне проекта, а
не внутри `sales/`). Копия шаблона Newspaper должна лежать по той же схеме.

```
sales/reports/newspaper/                       <- весь этот модуль (как есть)
<project_root>/templates/reports/newspaper/report.html  <- КОПИЯ шаблона (см. п.5)
<project_root>/static/newspaper/report.css     <- КОПИЯ css (см. п.5)
sales/admin.py                                  <- добавить вторую кнопку (см. п.3)
```

Модуль скопирован "как есть" в `sales/reports/newspaper/`, включая его
собственные `templates/` и `static/` — они там нужны, чтобы модуль был
самодостаточным и его можно было ревьюить отдельно. Но чтобы Django нашёл
шаблон и WeasyPrint нашёл CSS, нужно продублировать (или симлинкнуть) два
файла в конвенциональные места проекта — см. пункт 5. Именно так это уже
устроено для старого отчёта: `full_report.html` лежит в
`templates/reports/sales_plan_report/`, а `sales_plan_report.css` — в
`<project_root>/static/css/sales_plan_report/`.

## 1. Dependencies

В `requirements.txt` уже должен быть `weasyprint` (его использует
`sales_plan_report`) — новых требований к WeasyPrint нет.

Добавить новую зависимость:

```
matplotlib>=3.8
```

Это единственная новая библиотека. `pandas`/`numpy`/`scipy`, которые
использует `pages/matrix/data.py`, здесь **не нужны** — модуль остатков
получает данные через обычный `django.db.connection` и разбирает JSON
стандартной библиотекой (`json`, `re`), без pandas.

## 2. URLs (опционально)

Прямые URL не обязательны — основной сценарий это кнопка в Django Admin
(см. п.3), которая вызывает `build_newspaper_pdf_response` напрямую, как это
уже делает `print_plan_report` для старого отчёта.

Если всё же нужен прямой URL вида `/reports/newspaper/2026-08-18/`, добавьте
в главный `urls.py` проекта:

```python
from django.urls import include, path

urlpatterns += [
    path("reports/newspaper/", include("sales.reports.newspaper.urls")),
]
```

## 3. Django Admin — вторая кнопка

Существующая кнопка `plan_report_link` в `sales/admin.py` (класс
`MVSalesDailyAdmin`) не трогается. Рядом добавляется новая — `newspaper_link`.

**3.1. Импорт** — добавить рядом с существующим импортом exporter'а:

```python
from sales.reports.sales_plan_report.exporter import build_sales_plan_pdf_response
from sales.reports.newspaper.render.pdf import build_newspaper_pdf_response
```

**3.2. Метод-ссылка** — добавить в `MVSalesDailyAdmin` рядом с
`plan_report_link`:

```python
@admin.display(description="Newspaper")
def newspaper_link(self, obj):
    url = reverse(
        f"admin:{MV_Daily_Sales._meta.app_label}_{MV_Daily_Sales._meta.model_name}_newspaper",
        args=[obj.pk.isoformat()],
    )
    return format_html(
        '<a href="{}" target="_blank" title="COSMORELAX Daily Brief" '
        'style="text-decoration:none;font-size:14px;">📰</a>',
        url,
    )
```

**3.3. list_display** — добавить `"newspaper_link"` в кортеж `list_display`
класса `MVSalesDailyAdmin` (после `"plan_report_link"`):

```python
list_display = (
    "date", "amount", "quant", "orders", "ave_check", "dt", "cr",
    "rtr_ratio", "print_link", "plan_report_link", "newspaper_link",
)
```

**3.4. URL и view** — добавить в `get_urls()` рядом с существующим
`plan-report/`:

```python
path(
    "<slug:pk>/newspaper/",
    self.admin_site.admin_view(self.print_newspaper),
    name=f"{MV_Daily_Sales._meta.app_label}_{MV_Daily_Sales._meta.model_name}_newspaper",
),
```

и метод view рядом с `print_plan_report`:

```python
def print_newspaper(self, request, pk: str):
    try:
        d = date.fromisoformat(pk)
    except ValueError:
        raise Http404("Invalid date format. Expected YYYY-MM-DD")

    return build_newspaper_pdf_response(d, request=request)
```

После этого в списке `MV_Daily_Sales` в админке у каждой строки будет
одновременно `🖨` (обычная печать), `📊` (старый план-отчёт) и `📰` (новый
Newspaper). Ничего из существующего не удаляется.

## 4. Settings

Дополнительных изменений `settings.py` не требуется:

- Новых моделей и `INSTALLED_APPS` модуль не добавляет.
- WeasyPrint уже настроен и используется `sales_plan_report`.
- CSS читается напрямую с диска по `settings.BASE_DIR` (как и в
  `sales_plan_report/exporter.py`) — `STATICFILES_DIRS` менять не нужно.

Единственное, что важно проверить: `settings.BASE_DIR` действительно
указывает на корень проекта (там, где лежит верхнеуровневая папка
`static/`) — это уже так, раз работает старый отчёт.

## 5. Templates / Static — обязательный шаг

В `fr/settings.py` у вас `TEMPLATES[0]["DIRS"] = [BASE_DIR / "templates"]`,
и этот путь проверяется **раньше** APP_DIRS. Поэтому шаблон нужно класть в
корневую папку `templates/` проекта (НЕ в `sales/templates/`) — именно там
лежит и `reports/sales_plan_report/full_report.html` у старого отчёта.
Скопируйте (или сделайте symlink):

```bash
mkdir -p templates/reports/newspaper
cp sales/reports/newspaper/templates/reports/newspaper/report.html \
   templates/reports/newspaper/report.html

mkdir -p static/newspaper
cp sales/reports/newspaper/static/newspaper/report.css \
   static/newspaper/report.css
```

**Проверка:** `templates/reports/newspaper/report.html` не должен быть
0 байт — если он пустой или отсутствует, WeasyPrint напечатает пустой PDF
(так уже случалось при первой интеграции — Django молча подставляет пустой
шаблон вместо ошибки, если файл с таким именем есть, но пуст).

Если вы предпочитаете не дублировать файлы, альтернатива — добавить путь
модуля в `TEMPLATES[0]["DIRS"]` в `settings.py`:

```python
TEMPLATES[0]["DIRS"].append(BASE_DIR / "sales" / "reports" / "newspaper" / "templates")
```

но т.к. `sales_plan_report` использует именно копирование в
`sales/templates/...`, для единообразия проекта рекомендуется тот же приём.

## 6. System dependencies

WeasyPrint уже установлен и работает для `sales_plan_report`, поэтому
системные пакеты (Pango, Cairo, GDK-PixBuf, libffi и т.д.) на сервере уже
есть. Ничего дополнительно ставить не нужно.

Matplotlib никаких системных библиотек не требует — только доступные в
контейнере системные шрифты для рендера SVG-графиков (DejaVu Sans есть
практически везде "из коробки"; отчёт не завязан на конкретный шрифт для
графиков, только для HTML/CSS текста, который рендерит уже WeasyPrint).

## 7. Проверка после интеграции

1. `pip install -r requirements.txt` (подтянет matplotlib).
2. Выполнить шаги 3 и 5 выше.
3. Открыть Django Admin → `MV_Daily_Sales`, нажать на 📰 у любой строки.
4. Должен открыться PDF `COSMORELAX_Daily_Brief_<дата>.pdf` в новой вкладке.

## Что было изучено и переиспользовано

- **Кэш**: методология план/факта, прогноза и MoM/YoY полностью взята из
  `sales.reports.sales_plan_report.data.get_sales_plan_data` — Newspaper
  импортирует и использует её результат напрямую
  (`newspaper/data/cash.py`), не переизобретая расчёты.
- **Остатки**: источник — таблица `stocks_data` (поля `item_id`,
  `init_date`, `tot_available`, `tot_ordered`, `total`, `warehouse_stocks`,
  `warehouse_ordered`) и справочники `corporate_items` / `corporate_cattree`,
  как это установлено по `pages/matrix/data.py`. Запрос к остаткам —
  собственный (raw SQL через `django.db.connection`, а не через отдельный
  SQLAlchemy `ENGINE`, которым пользуется Dash-приложение), но таблицы и поля
  те же самые. Способ разбора `warehouse_stocks` (JSON-массив вида
  `"Магазин - N шт."`) портирован из `_parse_stock_qty` без изменения логики.
- **Стоимость остатков** нигде в исходных данных не хранится — она оценена
  через среднюю цену продажи товара за последние 90 дней
  (`sales_salesdata`), что явно помечено в отчёте как оценка с указанием
  процента покрытия.

## Чего не хватало / что пришлось додумывать

- Привязка `warehouse_stocks` к конкретному магазину/группе делается по
  точному совпадению нормализованного названия склада с названием магазина
  из cash-отчёта (`normalize_store_name`). Всё, что не совпало ни с одним
  магазином (например, "ОСНОВНОЙ склад"), относится к группе
  "Склады (вне магазинов)" — это реальная категория остатков, а не
  выдуманная; но если у вас есть более точный справочник соответствия
  склад → магазин (например, таблица с ID склада), лучше передать её сюда
  отдельным polем — тогда сопоставление будет точнее, чем по имени.
- Оценочная стоимость остатков — это управленческая оценка по средней цене
  продажи, а не бухгалтерская себестоимость/закупочная цена. Если в проекте
  есть таблица с реальной закупочной ценой/себестоимостью SKU, для точности
  её стоит подключить в `data/stocks.py` вместо (или в дополнение к) текущей
  оценке — дайте знать, где искать эти данные, и это можно будет уточнить.

## Развитие отчёта дальше

Архитектура рассчитана на постепенное добавление новых разделов (продажи,
маржа, цены, оборачиваемость, аномалии) по той же схеме:
`data/<раздел>.py` → `analytics/<раздел>.py` → `charts/<раздел>.py` →
блок в `templates/newspaper/report.html` + `payload["<раздел>"]` в
`data/payload.py`. Общая бизнес-логика, которую в будущем стоит вынести в
отдельный service-layer (общий для `sales_plan_report` и `newspaper`) —
это прежде всего разбор `warehouse_stocks`/`warehouse_ordered` (сейчас он
продублирован в упрощённом виде из `pages/matrix/data.py`, так как исходная
версия завязана на pandas/SQLAlchemy) и сопоставление названий складов с
магазинами.
