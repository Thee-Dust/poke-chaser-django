from django.apps import AppConfig


class CollectionsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "pokechaser.collections"

    def ready(self):
        import pokechaser.collections.signals  # noqa: F401
