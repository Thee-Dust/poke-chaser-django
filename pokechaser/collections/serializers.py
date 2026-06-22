from decimal import Decimal

from django.db.models import Sum
from rest_framework import serializers

from pokechaser.cards.models import Card
from pokechaser.collections.models import Collection, CollectionItem, CollectionItemPurchase
from pokechaser.collections.utils import get_tcgplayer_market_price


class CollectionSerializer(serializers.ModelSerializer):
    """Write serializer — used for create/update responses (no computed fields)."""
    class Meta:
        model = Collection
        fields = ["id", "name", "is_default", "created_at", "updated_at"]
        read_only_fields = ["id", "is_default", "created_at", "updated_at"]


class CollectionListSerializer(CollectionSerializer):
    """List serializer — adds card_count and total_market_value."""
    card_count = serializers.SerializerMethodField()
    total_market_value = serializers.SerializerMethodField()

    class Meta(CollectionSerializer.Meta):
        fields = CollectionSerializer.Meta.fields + ["card_count", "total_market_value"]

    def get_card_count(self, obj):
        return obj.items.count()

    def get_total_market_value(self, obj):
        total = Decimal("0.00")
        for item in obj.items.select_related("card").prefetch_related("purchases"):
            price = get_tcgplayer_market_price(item.card)
            if price is not None:
                total += Decimal(str(price)) * len(item.purchases.all())
        return str(total)


class CollectionItemPurchaseSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollectionItemPurchase
        fields = ["id", "acquired_date", "purchase_price", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]


class CardSummarySerializer(serializers.ModelSerializer):
    set_name = serializers.CharField(source="set.name", read_only=True)

    class Meta:
        model = Card
        fields = ["id", "name", "set_id", "set_name", "number", "rarity", "images", "tcgplayer"]


class CollectionItemSerializer(serializers.ModelSerializer):
    card = CardSummarySerializer(read_only=True)
    purchases = CollectionItemPurchaseSerializer(many=True, read_only=True)
    market_price = serializers.SerializerMethodField()
    market_value = serializers.SerializerMethodField()
    total_spent = serializers.SerializerMethodField()
    gain_loss = serializers.SerializerMethodField()

    class Meta:
        model = CollectionItem
        fields = [
            "id", "card", "purchases",
            "market_price", "market_value", "total_spent", "gain_loss",
            "created_at", "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def get_market_price(self, obj):
        price = get_tcgplayer_market_price(obj.card)
        return str(Decimal(str(price))) if price is not None else None

    def get_market_value(self, obj):
        price = get_tcgplayer_market_price(obj.card)
        if price is None:
            return None
        return str(Decimal(str(price)) * len(obj.purchases.all()))

    def get_total_spent(self, obj):
        total = sum(
            p.purchase_price for p in obj.purchases.all() if p.purchase_price is not None
        )
        return str(total) if total else "0.00"

    def get_gain_loss(self, obj):
        price = get_tcgplayer_market_price(obj.card)
        if price is None:
            return None
        market = Decimal(str(price)) * len(obj.purchases.all())
        spent = sum(
            p.purchase_price for p in obj.purchases.all() if p.purchase_price is not None
        )
        return str(market - (spent or Decimal("0.00")))


class CollectionDetailSerializer(CollectionListSerializer):
    """Detail serializer — adds total_spent, gain_loss, and items."""
    items = CollectionItemSerializer(many=True, read_only=True)
    total_spent = serializers.SerializerMethodField()
    gain_loss = serializers.SerializerMethodField()

    class Meta(CollectionListSerializer.Meta):
        fields = CollectionListSerializer.Meta.fields + ["total_spent", "gain_loss", "items"]

    def get_total_spent(self, obj):
        result = CollectionItemPurchase.objects.filter(
            item__collection=obj
        ).aggregate(total=Sum("purchase_price"))
        total = result["total"]
        return str(total) if total is not None else "0.00"

    def get_gain_loss(self, obj):
        market = Decimal(self.get_total_market_value(obj))
        spent = Decimal(self.get_total_spent(obj))
        return str(market - spent)
