from django.db import migrations


def create_default_roles(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    defaults = [
        {'name': 'مدير عام', 'name_en': 'Admin', 'is_system': True},
        {'name': 'محاسب', 'name_en': 'Accountant', 'is_system': True},
        {'name': 'موظّف استلام', 'name_en': 'Receiver', 'is_system': True},
        {'name': 'موظّف بيع', 'name_en': 'Seller', 'is_system': True},
        {'name': 'محصّل', 'name_en': 'Collector', 'is_system': True},
        {'name': 'موظّف', 'name_en': 'Employee', 'is_system': False},
    ]
    for data in defaults:
        Role.objects.get_or_create(name=data['name'], defaults=data)


def reverse(apps, schema_editor):
    Role = apps.get_model('accounts', 'Role')
    Role.objects.filter(is_system=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ('accounts', '0004_user_webauthn_credential_id_user_webauthn_enabled_and_more'),
    ]

    operations = [
        migrations.RunPython(create_default_roles, reverse),
    ]
