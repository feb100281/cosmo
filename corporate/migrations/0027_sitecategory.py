from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("corporate", "0026_stockreceipt"),
    ]

    operations = [
        migrations.CreateModel(
            name="SiteCategory",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("site_id", models.IntegerField(unique=True, verbose_name="id на сайте")),
                ("name", models.CharField(max_length=255, verbose_name="Раздел")),
                ("code", models.CharField(blank=True, default="", max_length=255, verbose_name="Код")),
                ("xml_id", models.CharField(blank=True, default="", max_length=100, verbose_name="xml_id (1С)")),
                ("depth", models.PositiveSmallIntegerField(default=1, verbose_name="Уровень")),
                ("sort", models.IntegerField(default=500, verbose_name="Сортировка")),
                ("active", models.BooleanField(default=True, verbose_name="Активен")),
                ("path", models.CharField(blank=True, default="", max_length=500, verbose_name="Путь")),
                ("in_last_upload", models.BooleanField(default=True, verbose_name="Есть в последней загрузке")),
                ("loaded_at", models.DateTimeField(auto_now=True, verbose_name="Загружено")),
                ("parent", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                             related_name="children", to="corporate.sitecategory",
                                             verbose_name="Родитель")),
                ("our_cat", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                              related_name="site_categories", to="corporate.cattree",
                                              verbose_name="Наша категория")),
                ("our_subcat", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL,
                                                 related_name="site_categories", to="corporate.subcategory",
                                                 verbose_name="Наша подкатегория")),
            ],
            options={
                "verbose_name": "Раздел каталога сайта",
                "verbose_name_plural": "Каталог сайта (Битрикс)",
                "ordering": ["path"],
            },
        ),
    ]
