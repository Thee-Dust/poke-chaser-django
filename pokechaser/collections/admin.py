from django.contrib import admin

from pokechaser.collections.models import Collection, CollectionItem


class CollectionItemInline(admin.TabularInline):
    model = CollectionItem
    extra = 0
    autocomplete_fields = ["card"]


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
