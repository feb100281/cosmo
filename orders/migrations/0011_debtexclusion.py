from django.db import migrations, models


def seed(apps, schema_editor):
    DebtExclusion = apps.get_model("orders", "DebtExclusion")
    DebtExclusion.objects.get_or_create(
        kind="client", value="Муховиков Максим Валерьевич",
        defaults={"reason": "other", "comment": "Долг не учитывается, анализ отдельно"},
    )


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0010_alter_mv_ordersitems_table_alter_orderscf_table"),
    ]

    operations = [
        migrations.CreateModel(
            name="DebtExclusion",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("kind", models.CharField(choices=[("client", "Клиент"), ("order", "Заказ (GUID или номер)")],
                                          default="order", max_length=10, verbose_name="Что исключаем")),
                ("value", models.CharField(help_text="Клиент — как в 1С, регистр не важен; заказ — GUID или номер (КСУТ-000715)",
                                           max_length=500, verbose_name="Клиент, GUID или номер заказа")),
                ("reason", models.CharField(choices=[("barter", "Бартер"), ("internal", "Свой / внутренний клиент"),
                                                     ("dispute", "Спорный, решается отдельно"), ("other", "Другое")],
                                            default="other", max_length=20, verbose_name="Причина")),
                ("comment", models.TextField(blank=True, default="", verbose_name="Комментарий")),
                ("is_active", models.BooleanField(default=True, verbose_name="Действует")),
                ("created_at", models.DateTimeField(auto_now_add=True, verbose_name="Добавлено")),
            ],
            options={"verbose_name": "Исключение из долгов", "verbose_name_plural": "Исключения из долгов",
                     "ordering": ["kind", "value"]},
        ),
        migrations.RunPython(seed, migrations.RunPython.noop),
    ]
