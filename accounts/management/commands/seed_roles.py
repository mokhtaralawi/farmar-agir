from django.core.management.base import BaseCommand
from accounts.models import Role


class Command(BaseCommand):
    help = 'إنشاء الأدوار الافتراضية'

    def handle(self, *args, **options):
        defaults = [
            {'name': 'مدير عام', 'name_en': 'Admin', 'is_system': True},
            {'name': 'محاسب', 'name_en': 'Accountant', 'is_system': True},
            {'name': 'موظّف استلام', 'name_en': 'Receiver', 'is_system': True},
            {'name': 'موظّف بيع', 'name_en': 'Seller', 'is_system': True},
            {'name': 'محصّل', 'name_en': 'Collector', 'is_system': True},
            {'name': 'موظّف', 'name_en': 'Employee', 'is_system': False},
        ]

        created = 0
        for data in defaults:
            obj, was_created = Role.objects.get_or_create(name=data['name'], defaults=data)
            if was_created:
                created += 1
                self.stdout.write(self.style.SUCCESS(f'  + {data["name"]}'))
            else:
                self.stdout.write(f'  - {data["name"]} (موجود مسبقاً)')

        self.stdout.write(self.style.SUCCESS(f'\nتم إنشاء {created} دور جديد من أصل {len(defaults)}'))
