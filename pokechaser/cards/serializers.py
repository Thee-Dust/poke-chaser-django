from rest_framework import serializers
from .models import CardSet, Card


class CardSetSerializer(serializers.ModelSerializer):
    class Meta:
        model = CardSet
        fields = [
            "id",
            "name",
            "series",
            "printed_total",
            "total",
            "ptcgo_code",
            "release_date",
            "legalities",
            "images",
        ]

class CardSerializer(serializers.ModelSerializer):
    set_name = serializers.CharField(source="set.name", read_only=True)

    class Meta:
        model = Card
        fields = [
            "id",
            "name",
            "supertype",
            "subtypes",
            "level",
            "hp",
            "types",
            "evolves_from",
            "evolves_to",
            "rules",
            "ancient_trait",
            "abilities",
            "attacks",
            "weaknesses",
            "resistances",
            "retreat_cost",
            "converted_retreat_cost",
            "number",
            "rarity",
            "regulation_mark",
            "artist",
            "flavor_text",
            "national_pokedex_numbers",
            "images",
            "legalities",
            "tcgplayer",
            "cardmarket",
            "set_id",
            "set_name",
        ]