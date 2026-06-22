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
from pokechaser.cards.views import PaginatedResponse
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
            qs = qs.prefetch_related(
                Prefetch(
                    "items",
                    queryset=CollectionItem.objects.select_related(
                        "card", "card__set"
                    ).prefetch_related("purchases"),
                )
            )
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
            queryset = (
                collection.items
                .select_related("card", "card__set")
                .prefetch_related("purchases")
            )
            page = self.paginate_queryset(queryset)
            serializer = CollectionItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        card_id = request.data.get("card_id")
        if not card_id:
            raise DRFValidationError({"card_id": ["This field is required."]})

        card = get_object_or_404(Card, id=card_id)
        item, created = CollectionItem.objects.get_or_create(collection=collection, card=card)

        purchases_data = request.data.get("purchases")
        if purchases_data:
            for p in purchases_data:
                CollectionItemPurchase.objects.create(
                    item=item,
                    acquired_date=p.get("acquired_date"),
                    purchase_price=p.get("purchase_price"),
                )
        else:
            CollectionItemPurchase.objects.create(item=item, acquired_date=None, purchase_price=None)

        item.refresh_from_db()
        serializer = CollectionItemSerializer(
            CollectionItem.objects.select_related("card", "card__set")
            .prefetch_related("purchases")
            .get(pk=item.pk)
        )
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)


class CollectionItemDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def delete(self, request, collection_pk, item_pk):
        item = _get_item(request, collection_pk, item_pk)
        item.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class CollectionItemPurchaseListView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, collection_pk, item_pk):
        item = _get_item(request, collection_pk, item_pk)
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
