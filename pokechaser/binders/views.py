import math

from django.db import transaction
from django.db.models import F, Max, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pokechaser.binders.models import Binder, BinderPage, BinderSlot
from pokechaser.binders.serializers import (
    BinderDetailSerializer,
    BinderListSerializer,
    BinderPageSerializer,
    BinderSerializer,
    BinderSlotSerializer,
)
from pokechaser.cards.models import Card


def _slots_qs():
    return BinderSlot.objects.select_related("card", "card__set")


def _resize_page(page, new_rows, new_cols):
    """
    Update a page's grid size. If the new capacity is smaller than the
    current number of filled slots, overflow cards are moved to new pages
    inserted immediately after the current page (inheriting the new size).
    All DB writes are wrapped in a single atomic transaction.
    """
    new_capacity = new_rows * new_cols

    with transaction.atomic():
        overflow_slots = list(
            page.slots.filter(position__gte=new_capacity).order_by("position")
        )

        if overflow_slots:
            num_new_pages = math.ceil(len(overflow_slots) / new_capacity)

            BinderPage.objects.filter(
                binder=page.binder,
                order__gt=page.order,
            ).update(order=F("order") + num_new_pages)

            for chunk_idx in range(num_new_pages):
                chunk = overflow_slots[chunk_idx * new_capacity:(chunk_idx + 1) * new_capacity]
                new_page = BinderPage.objects.create(
                    binder=page.binder,
                    name="",
                    order=page.order + chunk_idx + 1,
                    rows=new_rows,
                    cols=new_cols,
                )
                for new_position, slot in enumerate(chunk):
                    slot.page = new_page
                    slot.position = new_position
                    slot.save(update_fields=["page", "position"])

        page.rows = new_rows
        page.cols = new_cols
        page.save(update_fields=["rows", "cols", "updated_at"])


def _pages_qs():
    return BinderPage.objects.prefetch_related(Prefetch("slots", queryset=_slots_qs()))


class BinderViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    http_method_names = ["get", "post", "patch", "delete", "head", "options"]

    def get_queryset(self):
        qs = Binder.objects.filter(user=self.request.user)
        if self.action == "retrieve":
            qs = qs.prefetch_related(Prefetch("pages", queryset=_pages_qs()))
        return qs

    def get_serializer_class(self):
        if self.action == "list":
            return BinderListSerializer
        if self.action == "retrieve":
            return BinderDetailSerializer
        return BinderSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


def _get_binder(request, binder_pk):
    return get_object_or_404(Binder, pk=binder_pk, user=request.user)


def _get_page(request, binder_pk, pk):
    binder = _get_binder(request, binder_pk)
    return get_object_or_404(BinderPage, pk=pk, binder=binder)


class BinderPageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, binder_pk):
        binder = _get_binder(request, binder_pk)
        pages = binder.pages.prefetch_related(Prefetch("slots", queryset=_slots_qs()))
        serializer = BinderPageSerializer(pages, many=True)
        return Response(serializer.data)

    def post(self, request, binder_pk):
        binder = _get_binder(request, binder_pk)
        serializer = BinderPageSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        max_order = binder.pages.aggregate(max=Max("order"))["max"]
        next_order = (max_order + 1) if max_order is not None else 0
        order = request.data.get("order")
        if order is None:
            serializer.save(binder=binder, order=next_order)
        else:
            serializer.save(binder=binder)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class BinderPageDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, binder_pk, pk):
        page = _get_page(request, binder_pk, pk)
        page = _pages_qs().get(pk=page.pk)
        serializer = BinderPageSerializer(page)
        return Response(serializer.data)

    def patch(self, request, binder_pk, pk):
        page = _get_page(request, binder_pk, pk)
        serializer = BinderPageSerializer(page, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_rows = serializer.validated_data.get("rows", page.rows)
        new_cols = serializer.validated_data.get("cols", page.cols)
        grid_changing = (new_rows, new_cols) != (page.rows, page.cols)

        if grid_changing:
            # Save non-grid fields first, then handle overflow in one transaction.
            non_grid = {k: v for k, v in serializer.validated_data.items() if k not in ("rows", "cols")}
            if non_grid:
                for attr, value in non_grid.items():
                    setattr(page, attr, value)
                page.save(update_fields=list(non_grid.keys()) + ["updated_at"])
            _resize_page(page, new_rows, new_cols)
        else:
            serializer.save()

        page = _pages_qs().get(pk=page.pk)
        return Response(BinderPageSerializer(page).data)

    def delete(self, request, binder_pk, pk):
        page = _get_page(request, binder_pk, pk)
        page.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class BinderSlotView(APIView):
    permission_classes = [IsAuthenticated]

    def put(self, request, binder_pk, pk, position):
        page = _get_page(request, binder_pk, pk)
        if position >= page.capacity:
            raise DRFValidationError(
                {"position": [
                    f"Position {position} is out of bounds for a {page.rows}x{page.cols} grid "
                    f"(valid range: 0–{page.capacity - 1})."
                ]}
            )
        card_id = request.data.get("card_id")
        if not card_id:
            raise DRFValidationError({"card_id": ["This field is required."]})
        card = get_object_or_404(Card, id=card_id)
        slot, created = BinderSlot.objects.update_or_create(
            page=page,
            position=position,
            defaults={"card": card},
        )
        slot = BinderSlot.objects.select_related("card", "card__set").get(pk=slot.pk)
        serializer = BinderSlotSerializer(slot)
        return Response(serializer.data, status=status.HTTP_201_CREATED if created else status.HTTP_200_OK)

    def delete(self, request, binder_pk, pk, position):
        page = _get_page(request, binder_pk, pk)
        slot = get_object_or_404(BinderSlot, page=page, position=position)
        slot.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
