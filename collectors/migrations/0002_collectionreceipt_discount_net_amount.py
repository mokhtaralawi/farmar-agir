from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('collectors', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='collectionreceipt',
            name='discount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='الخصم'),
        ),
        migrations.AddField(
            model_name='collectionreceipt',
            name='net_amount',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=15, verbose_name='الصافي'),
        ),
    ]
