from django.apps import AppConfig


class InventoryConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'inventory'
    verbose_name = 'المخزون'

    def ready(self):
        pass  # inventory deductions are called explicitly from order views
