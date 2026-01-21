from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .models import ServiceOrder, OrderStatus
from .serializers import ServiceOrderSerializer


class ServiceOrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ServiceOrder.objects.all()

    @action(detail=True, methods=["post"])
    def start(self, request, pk=None):
        order = self.get_object()

        if order.status != OrderStatus.CREATED:
            return Response(
                {"detail": "Order can only be started from CREATED state."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = OrderStatus.IN_PROGRESS
        order.save(update_fields=["status"])

        return Response({"status": "IN_PROGRESS"})

    @action(detail=True, methods=["post"])
    def complete(self, request, pk=None):
        order = self.get_object()

        if order.status != OrderStatus.IN_PROGRESS:
            return Response(
                {"detail": "Only in-progress orders can be completed."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        order.status = OrderStatus.COMPLETED
        order.save(update_fields=["status"])

        return Response({"status": "COMPLETED"})