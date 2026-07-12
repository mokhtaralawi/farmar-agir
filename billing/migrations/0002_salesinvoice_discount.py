from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('billing', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='salesinvoice',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='خصم الفاتورة'),
        ),
    ]
