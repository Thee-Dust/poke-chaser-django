from django.conf import settings
from django.db import models

from pokechaser.core.models import BaseModel


class Collection(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="collections",
    )
    name = models.CharField(max_length=255)
    is_default = models.BooleanField(default=False)

    class Meta:
        ordering = ["-is_default", "name"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class CollectionItem(BaseModel):
    collection = models.ForeignKey(
        Collection,
        on_delete=models.CASCADE,
        related_name="items",
    )
    card = models.ForeignKey(
        "cards.Card",
        on_delete=models.CASCADE,
        related_name="collection_items",
    )

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["collection", "card"],
                name="unique_collection_card",
            ),
        ]
        ordering = ["card__set__release_date", "card__number", "card__name"]

    def __str__(self):
        return f"{self.card_id} in {self.collection.name}"
