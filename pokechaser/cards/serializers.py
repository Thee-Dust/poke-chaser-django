from rest_framework import serializers
from .models import CardSet


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