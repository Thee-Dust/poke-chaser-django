from django.contrib import admin

from pokechaser.cards.models import Card, CardSet


@admin.register(CardSet)
class CardSetAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "series", "release_date")


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "set", "supertype", "rarity")
    list_filter = ("set", "supertype")
    search_fields = ("id", "name")
