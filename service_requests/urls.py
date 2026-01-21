from rest_framework.routers import DefaultRouter
from .views import ServiceRequestViewSet
from .offer_views import ServiceOfferViewSet


router = DefaultRouter()
router.register(r"service-requests", ServiceRequestViewSet, basename="service-requests")
router.register(r"service-offers", ServiceOfferViewSet, basename="service-offers")

urlpatterns = router.urls
