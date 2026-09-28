from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import MovieViewSet, RegisterView, CreateBookingView, MyTicketsListView

router = DefaultRouter()
router.register(r"movie", MovieViewSet, basename="movie")

urlpatterns = [
    path("", include(router.urls)),
    path("api/token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("api/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("register/", RegisterView.as_view(), name="register"),
    path("buy-tickets/", CreateBookingView.as_view(), name="buy-tickets"),
    path("my-tickets/", MyTicketsListView.as_view(), name="my-tickets"),
]