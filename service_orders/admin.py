from django.contrib import admin
from .models import ServiceOrder


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'service_request', 'specialist_name', 'status', 'start_date', 'end_date']
    list_filter = ['status',]
    search_fields = ['service_request__id', 'provider_name', 'start_date', 'end_date']
    ordering = ['-created_at']