from django.contrib import admin
from .models import ServiceRequest, ServiceOffer


@admin.register(ServiceRequest)
class ServiceRequestAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'role_name']
    list_filter = ['status', 'experience_level', 'created_at']
    search_fields = ['external_id', 'role_name', 'technology']
    ordering = ['-created_at']


@admin.register(ServiceOffer)
class ServiceOfferAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['id', 'service_request__id', 'provider_name']
    ordering = ['-created_at']