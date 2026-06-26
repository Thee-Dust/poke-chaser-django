from django.urls import path
from rest_framework.routers import DefaultRouter

from pokechaser.binders import views

router = DefaultRouter()
router.register(r"", views.BinderViewSet, basename="binder")

urlpatterns = [
    path("sizes/", views.BinderSizesView.as_view(), name="binder-sizes"),
] + router.urls + [
    path(
        "<int:binder_pk>/pages/",
        views.BinderPageListView.as_view(),
        name="binder-page-list",
    ),
    path(
        "<int:binder_pk>/pages/<int:pk>/",
        views.BinderPageDetailView.as_view(),
        name="binder-page-detail",
    ),
    path(
        "<int:binder_pk>/pages/<int:pk>/slots/<int:position>/",
        views.BinderSlotView.as_view(),
        name="binder-slot",
    ),
]
