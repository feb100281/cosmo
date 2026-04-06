🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦
🛠️  ОБНОВЛЕНИЕ НА СЕРВЕРЕ
🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦🟦


🔐 ПОДКЛЮЧЕНИЕ
────────────────────────
ssh daria@37.46.129.233
ПАРОЛЬ


📂 ПРОЕКТ И ОКРУЖЕНИЕ
────────────────────────
cd cosmo
source venv/bin/activate


🔄 ОБНОВЛЕНИЕ КОДА
────────────────────────
git pull origin daria


🎨 СБОР СТАТИКИ
────────────────────────
python manage.py collectstatic


🧪 ПРОВЕРКА (на всякий случай)
────────────────────────
python manage.py check


🚀 ПЕРЕЗАПУСК СЕРВИСА
────────────────────────
sudo systemctl restart gunicorn.service


            
import pandas as pd

df = pd.read_excel('/Users/pavelustenko/Downloads/ЗАКАЗЫ 2026-04-05.xlsx',skiprows=1)
for col in df.columns:
    if col.startswith("Unnamed"):
        df  = df.drop(columns=col)
df.to_csv('/Users/pavelustenko/Downloads/norlal_orders.csv')