from django.db import models
import uuid


class OrderStatus(models.TextChoices):
    CREATED = "CREATED", "Created"
    IN_PROGRESS = "IN_PROGRESS", "In Progress"
    COMPLETED = "COMPLETED", "Completed"
    CANCELLED = "CANCELLED", "Cancelled"


class ServiceOrder(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    service_request = models.ForeignKey("service_requests.ServiceRequest", null=True, blank=True, on_delete=models.SET_NULL)
    winning_offer = models.ForeignKey("service_requests.ServiceOffer", null=True, blank=True, on_delete=models.SET_NULL)

    provider_id = models.CharField(max_length=128, null=True, blank=True)
    provider_name = models.CharField(max_length=128, null=True, blank=True)
    specialist_id = models.CharField(max_length=128, null=True, blank=True)
    specialist_name = models.CharField(max_length=128, null=True, blank=True)

    status = models.CharField(max_length=16, choices=OrderStatus.choices, default=OrderStatus.CREATED)

    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    man_days = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)