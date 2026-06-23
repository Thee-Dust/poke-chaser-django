from django.contrib import admin

from pokechaser.collections.models import Collection, CollectionItem, CollectionItemPurchase


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0
    autocomplete_fields = ["card"]


class CollectionItemPurchaseInline(admin.TabularInline):
    model = CollectionItemPurchase
    extra = 1
    fields = ("acquired_date", "purchase_price")


@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "is_default", "created_at")
    list_filter = ("is_default",)
    search_fields = ("name", "user__username", "user__email")
    inlines = [CollectionItemInline]


@admin.register(CollectionItem)
class CollectionItemAdmin(admin.ModelAdmin):
    list_display = ("card", "collection", "created_at")
    list_filter = ("collection",)
    search_fields = ("card__id", "card__name", "collection__name")
    autocomplete_fields = ["card", "collection"]
    inlines = [CollectionItemPurchaseInline]


@admin.register(CollectionItemPurchase)
class CollectionItemPurchaseAdmin(admin.ModelAdmin):
    list_display = ("item", "purchase_price", "acquired_date", "created_at")
    list_filter = ("acquired_date",)
    search_fields = ("item__card__name", "item__collection__name")
