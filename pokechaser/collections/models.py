from django.conf import settings
from django.core.exceptions import ValidationError
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

    def delete(self, *args, **kwargs):
        if self.is_default:
            raise ValidationError("The default collection cannot be deleted.")
        super().delete(*args, **kwargs)


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
    quantity = models.PositiveIntegerField(default=1)

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


class CollectionItemPurchase(BaseModel):
    item = models.ForeignKey(
        CollectionItem,
        on_delete=models.CASCADE,
        related_name="purchases",
    )
    acquired_date = models.DateField(null=True, blank=True)
    purchase_price = models.DecimalField(
        max_digits=10, decimal_places=2, null=True, blank=True
    )

    class Meta:
        ordering = ["acquired_date", "created_at"]

    def __str__(self):
        price = f"${self.purchase_price}" if self.purchase_price is not None else "no price"
        date = str(self.acquired_date) if self.acquired_date else "no date"
        return f"{self.item} — {price} on {date}"
