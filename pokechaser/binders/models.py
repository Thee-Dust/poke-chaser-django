from django.conf import settings
from django.db import models

from pokechaser.core.models import BaseModel

ALLOWED_GRID_SIZES = {(2, 2), (3, 3), (3, 4), (4, 4)}


class Binder(BaseModel):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="binders",
    )
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.user.username})"


class BinderPage(BaseModel):
    binder = models.ForeignKey(
        Binder,
        on_delete=models.CASCADE,
        related_name="pages",
    )
    name = models.CharField(max_length=255, blank=True)
    order = models.PositiveIntegerField(default=0)
    rows = models.PositiveSmallIntegerField(default=3)
    cols = models.PositiveSmallIntegerField(default=3)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        label = self.name or f"Page {self.order + 1}"
        return f"{label} — {self.binder.name}"

    @property
    def capacity(self):
        return self.rows * self.cols


class BinderSlot(BaseModel):
    page = models.ForeignKey(
        BinderPage,
        on_delete=models.CASCADE,
        related_name="slots",
    )
    card = models.ForeignKey(
        "cards.Card",
        on_delete=models.CASCADE,
        related_name="binder_slots",
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]
        constraints = [
            models.UniqueConstraint(
                fields=["page", "position"],
                name="unique_binder_page_position",
            ),
        ]

    def __str__(self):
        return f"{self.card_id} at position {self.position} on {self.page}"
