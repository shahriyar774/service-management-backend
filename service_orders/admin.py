from django.contrib import admin
from .models import *


@admin.register(ServiceOrder)
class ServiceOrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'title', 'status', 'start_date', 'original_end_date']
    list_filter = ['status',]
    ordering = ['-created_at']


@admin.register(ServiceOrderExtension)
class ServiceOrderExtensionAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'new_end_date',]
    list_filter = ['status',]
    ordering = ['-created_at']


@admin.register(ServiceOrderSubstitution)
class ServiceOrderSubstitutionAdmin(admin.ModelAdmin):
    list_display = ['id', 'status', 'outgoing_specialist_name', 'incoming_specialist_name']
    list_filter = ['status',]
    ordering = ['-created_at']