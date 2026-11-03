from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("dashboard", "0007_delete_catdash_delete_salesdash"),
    ]

    operations = [
        migrations.CreateModel(
            name="MeetingBrief",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ],
            options={
                "verbose_name": "Отчёт к совещанию",
                "verbose_name_plural": "Отчёт к совещанию",
                "managed": False,
                "default_permissions": ("view",),
            },
        ),
    ]
