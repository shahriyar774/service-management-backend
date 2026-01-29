from django.db import models
import uuid


class RequestStatus(models.TextChoices):
    DRAFT  = "DRAFT", "Draft"
    OPEN      = "OPEN", "Open"
    CLOSED    = "CLOSED", "Closed"
    AWARDED   = "AWARDED", "Awarded"
    CANCELLED = "CANCELLED", "Cancelled"

class ExperienceLevel(models.TextChoices):
    EXPERT  = "EXPERT", "Expert"
    LEAD      = "LEAD", "Lead"
    SENIOR    = "SENIOR", "Senior"
    MID   = "MID", "Mid"
    JUNIOR = "JUNIOR", "Junior"


class ServiceRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title               = models.CharField(max_length=128)
    role_name           = models.CharField(max_length=128) # requested role
    technology          = models.CharField(max_length=128, blank=True)
    specialization      = models.CharField(max_length=64, blank=True)
    experience_level    = models.CharField(max_length=16, choices=ExperienceLevel.choices, default=ExperienceLevel.JUNIOR)
    start_date          = models.DateField(null=True, blank=True)
    end_date            = models.DateField(null=True, blank=True)
    expected_man_days   = models.PositiveIntegerField(null=True, blank=True)
    criteria_json       = models.JSONField(default=dict, blank=True)
    status              = models.CharField(max_length=16, choices=RequestStatus.choices, default=RequestStatus.OPEN)
    task_description    = models.TextField(blank=True)
    offer_deadline      = models.DateField(null=True, blank=True)
    process_id          = models.CharField(max_length=128, blank=True, null=True)
    created_at          = models.DateTimeField(auto_now_add=True)
    updated_at          = models.DateTimeField(auto_now=True)


class ServiceOffer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    external_id = models.CharField(max_length=128, null=True, blank=True)
    service_request = models.ForeignKey(ServiceRequest, on_delete=models.CASCADE, related_name="offers")
    provider_id = models.CharField(max_length=128, null=True, blank=True)
    provider_name = models.CharField(max_length=128, null=True, blank=True)
    specialist_id = models.CharField(max_length=128, null=True, blank=True)
    specialist_name = models.CharField(max_length=128, null=True, blank=True)
    status       = models.CharField(max_length=16, blank=True, null=True)
    daily_rate   = models.DecimalField(max_digits=10, decimal_places=2)
    travel_cost  = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_cost   = models.DecimalField(max_digits=12, decimal_places=2)
    notes        = models.TextField(blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)


class ProjectRequest(models.Model):
    project_id = models.CharField(max_length=128)
    project_name = models.CharField(max_length=128)
    specialist_id = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    