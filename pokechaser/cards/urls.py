from django.urls import include, path
from rest_framework import routers
from . import views


router = routers.DefaultRouter()
router.register(r"cardSet", views.CardSetViewSet, basename="cardset")


urlpatterns = [
    path("", include(router.urls)),
]