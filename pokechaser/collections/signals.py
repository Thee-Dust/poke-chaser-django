from django.conf import settings
from django.db.models.signals import post_save
from django.dispatch import receiver


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def create_default_collection(sender, instance, created, **kwargs):
    if created:
        from pokechaser.collections.models import Collection
        Collection.objects.create(
            user=instance,
            name="My Collection",
            is_default=True,
        )
