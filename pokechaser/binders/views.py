import math

from django.db import transaction
from django.db.models import F, Max, Prefetch
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from pokechaser.binders.models import ALLOWED_GRID_SIZES, Binder, BinderPage, BinderSlot
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


def _pages_qs():
    return BinderPage.objects.select_related("binder").prefetch_related(
        Prefetch("slots", queryset=_slots_qs())
    )


def _overflow_page(page, new_capacity):
    """
    If any slots on `page` sit at position >= new_capacity, move them to
    new pages inserted immediately after the current page.
    The binder's rows/cols are already updated before this is called.
    """
    overflow_slots = list(
        page.slots.filter(position__gte=new_capacity).order_by("position")
    )
    if not overflow_slots:
        return

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
        )
        for new_position, slot in enumerate(chunk):
            slot.page = new_page
            slot.position = new_position
            slot.save(update_fields=["page", "position"])


def _resize_binder(binder, new_rows, new_cols):
    """
    Update the binder's grid size. For each existing page, any slots beyond
    the new capacity overflow into new pages inserted right after that page.
    All writes run in a single atomic transaction.
    """
    new_capacity = new_rows * new_cols

    with transaction.atomic():
        binder.rows = new_rows
        binder.cols = new_cols
        binder.save(update_fields=["rows", "cols", "updated_at"])

        # Snapshot PKs in order before any order shifts occur.
        page_pks = list(
            BinderPage.objects.filter(binder=binder).order_by("order").values_list("pk", flat=True)
        )
        for pk in page_pks:
            page = BinderPage.objects.select_related("binder").get(pk=pk)
            _overflow_page(page, new_capacity)


class BinderSizesView(APIView):
    permission_classes = []
    authentication_classes = []

    def get(self, request):
        sizes = sorted(ALLOWED_GRID_SIZES)
        data = [
            {
                "rows": rows,
                "cols": cols,
                "label": f"{rows}x{cols}",
                "capacity": rows * cols,
            }
            for rows, cols in sizes
        ]
        return Response(data)


def _get_binder(request, binder_pk):
    return get_object_or_404(Binder, pk=binder_pk, user=request.user)


def _get_page(request, binder_pk, pk):
    binder = _get_binder(request, binder_pk)
    return get_object_or_404(BinderPage, pk=pk, binder=binder)


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

    def partial_update(self, request, *args, **kwargs):
        binder = self.get_object()
        serializer = BinderSerializer(binder, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        new_rows = serializer.validated_data.get("rows", binder.rows)
        new_cols = serializer.validated_data.get("cols", binder.cols)
        grid_changing = (new_rows, new_cols) != (binder.rows, binder.cols)

        if grid_changing:
            non_grid = {k: v for k, v in serializer.validated_data.items() if k not in ("rows", "cols")}
            if non_grid:
                for attr, value in non_grid.items():
                    setattr(binder, attr, value)
                binder.save(update_fields=list(non_grid.keys()) + ["updated_at"])
            _resize_binder(binder, new_rows, new_cols)
        else:
            serializer.save()

        binder.refresh_from_db()
        return Response(BinderSerializer(binder).data)


class BinderPageListView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, binder_pk):
        binder = _get_binder(request, binder_pk)
        pages = binder.pages.select_related("binder").prefetch_related(
            Prefetch("slots", queryset=_slots_qs())
        )
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
        page = BinderPage.objects.select_related("binder").get(pk=page.pk)
        if position >= page.capacity:
            raise DRFValidationError(
                {"position": [
                    f"Position {position} is out of bounds for a "
                    f"{page.binder.rows}x{page.binder.cols} grid "
                    f"(valid range: 0\u2013{page.capacity - 1})."
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
