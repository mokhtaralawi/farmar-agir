import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ActivityLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(max_length=30, verbose_name='العملية')),
                ('description', models.TextField(verbose_name='الوصف')),
                ('reference_type', models.CharField(blank=True, max_length=50, verbose_name='نوع المرجع')),
                ('reference_id', models.PositiveIntegerField(blank=True, null=True, verbose_name='رقم المرجع')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='عنوان IP')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='التاريخ')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL, verbose_name='المستخدم')),
            ],
            options={
                'verbose_name': 'سجل نشاط',
                'verbose_name_plural': 'سجل النشاطات',
                'ordering': ['-created_at'],
            },
        ),
    ]
