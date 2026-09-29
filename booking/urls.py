from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

from .views import (
    CreateBookingView,
    MovieViewSet,
    MyTicketsListView,
    RegisterView,
    ShowtimeViewSet,
    HallViewSet 
)

router = DefaultRouter()
router.register(r"movies", MovieViewSet, basename="movie")
router.register(r"showtimes", ShowtimeViewSet, basename="showtime")
router.register(r"halls", HallViewSet, basename="hall")

urlpatterns = [
    path("", include(router.urls)),
    
    path("register/", RegisterView.as_view(), name="register"),
    path("token/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    
    path("buy-tickets/", CreateBookingView.as_view(), name="buy-tickets"),
    path("my-tickets/", MyTicketsListView.as_view(), name="my-tickets"),
]