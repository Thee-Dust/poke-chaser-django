from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response
from rest_framework.utils.urls import replace_query_param, remove_query_param
from django.db.models import F, FloatField, Q, Value
from django.db.models.functions import Coalesce, Length
from .models import Card, CardSet
from .serializers import CardSerializer, CardSetSerializer

SORT_OPTIONS = {
    "release_date_desc": ["-release_date", "name"],
    "release_date_asc": ["release_date", "name"],
    "name_asc": ["name"],
    "name_desc": ["-name"],
}


class PaginatedResponse(PageNumberPagination):
    page_size = 18
    def get_paginated_response(self, data):
        page = self.page
        return Response({
            "links": {
                "first": self._page_link(1),
                "last": self._page_link(page.paginator.num_pages),
                "next": self.get_next_link(),
                "prev": self.get_previous_link(),
            },
            "meta": {
                "pagination": {
                    "page": page.number,
                    "pages": page.paginator.num_pages,
                    "count": page.paginator.count,
                }
            },
            "results": data,
        })
    def _page_link(self, page_number):
        url = self.request.build_absolute_uri()
        if page_number == 1:
            return remove_query_param(url, self.page_query_param)
        return replace_query_param(url, self.page_query_param, page_number)

class CardSetPagination(PaginatedResponse):
    page_size = 18

class CardPagination(PaginatedResponse):
    page_size = 24

def search_cards(queryset, search):
    if not search:
        return queryset
    return queryset.filter(
        Q(name__icontains=search)
        | Q(set__name__icontains=search)
        | Q(rarity__icontains=search)
        | Q(supertype__icontains=search)
    )


def sort_cards(queryset, sort):
    number_order = (Length("number"), "number")
    if sort == "name_asc":
        return queryset.order_by("name")
    if sort == "name_desc":
        return queryset.order_by("-name")
    if sort in ("price_desc", "price_asc"):
        queryset = queryset.annotate(
            market_price=Coalesce(
                F("tcgplayer__prices__normal__market"),
                F("tcgplayer__prices__holofoil__market"),
                F("tcgplayer__prices__reverseHolofoil__market"),
                Value(None),
                output_field=FloatField(),
            )
        )
        if sort == "price_desc":
            return queryset.order_by(
                F("market_price").desc(nulls_last=True),
                *number_order,
            )
        return queryset.order_by(
            F("market_price").asc(nulls_last=True),
            *number_order,
        )
    # default: "number_asc" or unknown
    return queryset.order_by(*number_order)

class CardSetViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CardSetSerializer
    pagination_class = CardSetPagination

    def get_queryset(self):
        sort = self.request.query_params.get("sort", "release_date_desc")
        ordering = SORT_OPTIONS.get(sort, SORT_OPTIONS["release_date_desc"])
        return CardSet.objects.all().order_by(*ordering)

    @action(detail=True, pagination_class=CardPagination)
    def cards(self, request, pk=None):
        card_set = self.get_object()
        search = request.query_params.get("search")
        sort = request.query_params.get("sort", "number_asc")
        queryset = search_cards(card_set.cards.select_related("set"), search)
        queryset = sort_cards(queryset, sort)
        page = self.paginate_queryset(queryset)
        serializer = CardSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)


class CardViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CardSerializer
    pagination_class = CardPagination
    lookup_field = "id"

    def get_queryset(self):
        queryset = Card.objects.select_related("set")
        queryset = search_cards(queryset, self.request.query_params.get("search"))
        return sort_cards(queryset, self.request.query_params.get("sort", "number_asc"))