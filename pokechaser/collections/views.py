from django.core.exceptions import ValidationError as DjangoValidationError
from django.db.models import Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pokechaser.cards.models import Card
from pokechaser.cards.serializers import CardSerializer
from pokechaser.cards.views import PaginatedResponse, search_cards, sort_cards
from pokechaser.collections.models import Collection, CollectionItem, CollectionItemPurchase
from pokechaser.collections.serializers import (
    CollectionSerializer,
    CollectionListSerializer,
    CollectionDetailSerializer,
    CollectionItemSerializer,
    CollectionItemPurchaseSerializer,
)


class CollectionItemPagination(PaginatedResponse):
    page_size = 24


class CollectionCardsPagination(PaginatedResponse):
    page_size = 6


def _get_collection(request, collection_pk):
    return get_object_or_404(Collection, pk=collection_pk, user=request.user)


def _get_item(request, collection_pk, item_pk):
    collection = _get_collection(request, collection_pk)
    return get_object_or_404(CollectionItem, pk=item_pk, collection=collection)


class CollectionViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    serializer_class = CollectionSerializer
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Collection.objects.filter(user=self.request.user)
        if self.action == "retrieve":
            sort = self.request.query_params.get("sort", "price_desc")
            items_qs = sort_cards(
                CollectionItem.objects.select_related("card", "card__set").prefetch_related("purchases"),
                sort,
                prefix="card__",
            )
            qs = qs.prefetch_related(Prefetch("items", queryset=items_qs))
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return CollectionListSerializer
        if self.action == "retrieve":
            return CollectionDetailSerializer
        return CollectionSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        try:
            instance.delete()
        except DjangoValidationError as exc:
            raise DRFValidationError({"detail": exc.message})
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["get", "post"], pagination_class=CollectionItemPagination)
    def items(self, request, pk=None):
        collection = self.get_object()

        if request.method == "GET":
            sort = request.query_params.get("sort", "price_desc")
            queryset = sort_cards(
                collection.items.select_related("card", "card__set").prefetch_related("purchases"),
                sort,
                prefix="card__",
            )
            page = self.paginate_queryset(queryset)
            serializer = CollectionItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        card_id = request.data.get("card_id")
        if not card_id:
            raise DRFValidationError({"card_id": ["This field is required."]})

        quantity = request.data.get("quantity", 1)
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise DRFValidationError({"quantity": ["Must be a positive integer."]})
        if quantity < 1:
            raise DRFValidationError({"quantity": ["Must be at least 1."]})

        purchases_data = request.data.get("purchases") or []
        if len(purchases_data) > quantity:
            raise DRFValidationError(
                {"purchases": [f"Cannot have more purchase records ({len(purchases_data)}) than quantity ({quantity})."]}
            )

        card = get_object_or_404(Card, id=card_id)
        item, created = CollectionItem.objects.get_or_create(
            collection=collection,
            card=card,
            defaults={"quantity": quantity},
        )

        if not created:
            new_quantity = item.quantity + quantity
            existing_purchases = item.purchases.count()
            if existing_purchases + len(purchases_data) > new_quantity:
                raise DRFValidationError(
                    {"purchases": ["Total purchase records would exceed the updated quantity."]}
                )
            item.quantity = new_quantity
            item.save(update_fields=["quantity"])

        for p in purchases_data:
            CollectionItemPurchase.objects.create(
                item=item,
                acquired_date=p.get("acquired_date"),
                purchase_price=p.get("purchase_price"),
            )

        item.refresh_from_db()
        serializer = CollectionItemSerializer(
            CollectionItem.objects.select_related("card", "card__set")
            .prefetch_related("purchases")
            .get(pk=item.pk)
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    @action(detail=True, methods=["get"], pagination_class=CollectionCardsPagination)
    def cards(self, request, pk=None):
        collection = self.get_object()
        sort = request.query_params.get("sort", "name_asc")
        search = request.query_params.get("search")
        queryset = collection.items.select_related("card", "card__set")
        queryset = search_cards(queryset, search, prefix="card__")
        queryset = sort_cards(queryset, sort, prefix="card__")
        page = self.paginate_queryset(queryset)
        cards = [item.card for item in page]
        serializer = CardSerializer(cards, many=True)
        return self.get_paginated_response(serializer.data)


class CollectionItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request, collection_pk, item_pk):
        item = _get_item(request, collection_pk, item_pk)
        quantity = request.data.get("quantity")
        if quantity is None:
            raise DRFValidationError({"quantity": ["This field is required."]})
        try:
            quantity = int(quantity)
        except (TypeError, ValueError):
            raise DRFValidationError({"quantity": ["Must be a positive integer."]})
        if quantity < 1:
            raise DRFValidationError({"quantity": ["Must be at least 1."]})
        if item.purchases.count() > quantity:
            raise DRFValidationError(
                {"quantity": ["Cannot be less than the number of existing purchase records."]}
            )
        item.quantity = quantity
        item.save(update_fields=["quantity"])
        serializer = CollectionItemSerializer(
            CollectionItem.objects.select_related("card", "card__set")
            .prefetch_related("purchases")
            .get(pk=item.pk)
        )
        return Response(serializer.data)

    def delete(self, request, collection_pk, item_pk):
        item = _get_item(request, collection_pk, item_pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CollectionItemPurchaseListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, collection_pk, item_pk):
        item = _get_item(request, collection_pk, item_pk)
        if item.purchases.count() >= item.quantity:
            raise DRFValidationError(
                {"purchases": [f"Cannot add more purchase records. Item quantity is {item.quantity}."]}
            )
        serializer = CollectionItemPurchaseSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(item=item)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class CollectionItemPurchaseDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def _get_purchase(self, request, collection_pk, item_pk, pk):
        item = _get_item(request, collection_pk, item_pk)
        return get_object_or_404(CollectionItemPurchase, pk=pk, item=item)

    def patch(self, request, collection_pk, item_pk, pk):
        purchase = self._get_purchase(request, collection_pk, item_pk, pk)
        serializer = CollectionItemPurchaseSerializer(purchase, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, collection_pk, item_pk, pk):
        purchase = self._get_purchase(request, collection_pk, item_pk, pk)
        item = purchase.item
        purchase.delete()
        if not item.purchases.exists():
            item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
