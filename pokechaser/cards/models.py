from django.db import models

from pokechaser.core.models import BaseModel


class CardSet(BaseModel):
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    series = models.CharField(max_length=255)
    printed_total = models.IntegerField()
    total = models.IntegerField()
    ptcgo_code = models.CharField(max_length=20, blank=True)
    release_date = models.DateField(null=True, blank=True)
    updated_at_api = models.DateTimeField(null=True, blank=True)
    legalities = models.JSONField(default=dict)
    images = models.JSONField(default=dict)

    class Meta:
        verbose_name = "set"
        verbose_name_plural = "sets"
        ordering = ["-release_date", "name"]

    def __str__(self):
        return self.name


class Card(BaseModel):
    id = models.CharField(max_length=50, primary_key=True)
    set = models.ForeignKey(CardSet, on_delete=models.CASCADE, related_name="cards")
    name = models.CharField(max_length=255)
    supertype = models.CharField(max_length=50)
    subtypes = models.JSONField(default=list)
    hp = models.CharField(max_length=10, blank=True)
    types = models.JSONField(default=list)
    evolves_from = models.CharField(max_length=255, blank=True)
    attacks = models.JSONField(default=list)
    weaknesses = models.JSONField(default=list)
    resistances = models.JSONField(default=list)
    retreat_cost = models.JSONField(default=list)
    converted_retreat_cost = models.IntegerField(null=True, blank=True)
    number = models.CharField(max_length=20)
    artist = models.CharField(max_length=255, blank=True)
    rarity = models.CharField(max_length=100, blank=True)
    flavor_text = models.TextField(blank=True)
    national_pokedex_numbers = models.JSONField(default=list)
    legalities = models.JSONField(default=dict)
    images = models.JSONField(default=dict)
    tcgplayer = models.JSONField(null=True, blank=True)
    cardmarket = models.JSONField(null=True, blank=True)
    

    def __str__(self):
        return self.name
