from rest_framework import serializers

from pokechaser.binders.models import ALLOWED_GRID_SIZES, Binder, BinderPage, BinderSlot
from pokechaser.cards.models import Card

_GRID_CHOICES = sorted(ALLOWED_GRID_SIZES)
_GRID_DISPLAY = ", ".join(f"{r}x{c}" for r, c in _GRID_CHOICES)


class CardSummarySerializer(serializers.ModelSerializer):
    set_name = serializers.CharField(source="set.name", read_only=True)

    class Meta:
        model = Card
        fields = ["id", "name", "set_id", "set_name", "number", "rarity", "images", "tcgplayer"]


class BinderSlotSerializer(serializers.ModelSerializer):
    card = CardSummarySerializer(read_only=True)

    class Meta:
        model = BinderSlot
        fields = ["id", "position", "card", "created_at", "updated_at"]
        read_only_fields = ["id", "position", "card", "created_at", "updated_at"]


class BinderPageSerializer(serializers.ModelSerializer):
    slots = BinderSlotSerializer(many=True, read_only=True)
    capacity = serializers.SerializerMethodField()

    class Meta:
        model = BinderPage
        fields = ["id", "name", "order", "capacity", "slots", "created_at", "updated_at"]
        read_only_fields = ["id", "capacity", "created_at", "updated_at"]

    def get_capacity(self, obj):
        return obj.capacity


class BinderSerializer(serializers.ModelSerializer):
    capacity = serializers.SerializerMethodField()

    class Meta:
        model = Binder
        fields = ["id", "name", "rows", "cols", "capacity", "created_at", "updated_at"]
        read_only_fields = ["id", "capacity", "created_at", "updated_at"]

    def get_capacity(self, obj):
        return obj.capacity

    def validate(self, data):
        rows = data.get("rows", self.instance.rows if self.instance else 3)
        cols = data.get("cols", self.instance.cols if self.instance else 3)
        if (rows, cols) not in ALLOWED_GRID_SIZES:
            raise serializers.ValidationError(
                {"rows/cols": [f"Grid size {rows}x{cols} is not allowed. Choose one of: {_GRID_DISPLAY}."]}
            )
        return data


class BinderListSerializer(BinderSerializer):
    page_count = serializers.SerializerMethodField()

    class Meta(BinderSerializer.Meta):
        fields = BinderSerializer.Meta.fields + ["page_count"]

    def get_page_count(self, obj):
        return obj.pages.count()


class BinderDetailSerializer(BinderListSerializer):
    pages = BinderPageSerializer(many=True, read_only=True)

    class Meta(BinderListSerializer.Meta):
        fields = BinderListSerializer.Meta.fields + ["pages"]
