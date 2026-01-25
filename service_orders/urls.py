from rest_framework.routers import DefaultRouter

from .views import *

router = DefaultRouter()
router.register(r"service-orders", ServiceOrderViewSet, basename="service-orders")
router.register(r"extensions", ServiceOrderExtensionViewSet, basename="extensions")
router.register(r"substitutions", ServiceOrderSubstitutionViewSet, basename="substitutions")

urlpatterns = router.urls