from django.urls import path
from rest_framework.routers import DefaultRouter

from pokechaser.collections import views

router = DefaultRouter()
router.register(r"", views.CollectionViewSet, basename="collection")

urlpatterns = router.urls + [
    path(
        "<int:collection_pk>/items/<int:item_pk>/",
        views.CollectionItemDetailView.as_view(),
        name="collection-item-detail",
    ),
    path(
        "<int:collection_pk>/items/<int:item_pk>/purchases/",
        views.CollectionItemPurchaseListView.as_view(),
        name="collection-item-purchase-list",
    ),
    path(
        "<int:collection_pk>/items/<int:item_pk>/purchases/<int:pk>/",
        views.CollectionItemPurchaseDetailView.as_view(),
        name="collection-item-purchase-detail",
    ),
]
