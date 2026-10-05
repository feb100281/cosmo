from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("corporate", "0025_barcode_spec"),
    ]

    operations = [
        migrations.CreateModel(
            name="StockReceipt",
            fields=[
                ("id", models.BigAutoField(primary_key=True, serialize=False)),
                ("receipt_guid", models.CharField(max_length=64, verbose_name="GUID прихода")),
                ("receipt_number", models.CharField(blank=True, max_length=100, null=True, verbose_name="№ прихода")),
                ("receipt_date", models.DateField(blank=True, null=True, verbose_name="Дата прихода")),
                ("item_guid", models.CharField(blank=True, max_length=64, null=True)),
                ("char_guid", models.CharField(blank=True, max_length=64, null=True)),
                ("warehouse_guid", models.CharField(blank=True, max_length=64, null=True)),
                ("fullname", models.CharField(blank=True, max_length=500, null=True, verbose_name="Номенклатура")),
                ("characteristic", models.TextField(blank=True, null=True, verbose_name="Характеристика")),
                ("warehouse", models.CharField(blank=True, max_length=255, null=True, verbose_name="Склад")),
                ("barcode", models.CharField(blank=True, max_length=100, null=True, verbose_name="Штрихкод")),
                ("qty", models.DecimalField(decimal_places=3, max_digits=14, verbose_name="Кол-во")),
                ("price_purchase", models.DecimalField(blank=True, decimal_places=2, max_digits=14, null=True, verbose_name="Цена без НДС")),
                ("amount_purchase", models.DecimalField(blank=True, decimal_places=2, max_digits=16, null=True, verbose_name="Сумма без НДС")),
                ("loaded_at", models.DateTimeField(verbose_name="Загружено")),
                ("item", models.ForeignKey(blank=True, db_column="item_id", db_constraint=False, null=True,
                                           on_delete=django.db.models.deletion.DO_NOTHING,
                                           related_name="+", to="corporate.items", verbose_name="Товар")),
            ],
            options={
                "verbose_name": "Приход",
                "verbose_name_plural": "Приходы",
                "db_table": "stock_receipts",
                "managed": False,
            },
        ),
    ]
