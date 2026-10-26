from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("orders", "0011_debtexclusion"),
    ]

    operations = [
        migrations.AlterField(
            model_name="debtexclusion",
            name="reason",
            field=models.CharField(
                choices=[("barter", "Бартер"), ("internal", "Свой / внутренний клиент"),
                         ("dispute", "Спорный, решается отдельно"),
                         ("commission", "Комиссионер, оплата по отчёту"), ("other", "Другое")],
                default="other", max_length=20, verbose_name="Причина",
            ),
        ),
    ]
