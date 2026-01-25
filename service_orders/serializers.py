from rest_framework import serializers
from decimal import Decimal
from django.utils import timezone

from .models import *


class ServiceOrderDetailSerializer(serializers.ModelSerializer):
    consumed_man_days = serializers.ReadOnlyField()
    remaining_man_days = serializers.ReadOnlyField()
    has_been_extended = serializers.ReadOnlyField()
    has_been_substituted = serializers.ReadOnlyField()
    is_active = serializers.ReadOnlyField()
    can_request_extension = serializers.SerializerMethodField()
    can_request_substitution = serializers.SerializerMethodField()
    pending_extension_id = serializers.SerializerMethodField()
    pending_substitution_id = serializers.SerializerMethodField()
    
    class Meta:
        model = ServiceOrder
        fields = '__all__'
    
    def get_can_request_extension(self, obj):
        return obj.can_request_extension()
    
    def get_can_request_substitution(self, obj):
        return obj.can_request_substitution()
    
    def get_pending_extension_id(self, obj):
        latest_extension = obj.extensions.order_by('-created_at').first()
        
        if latest_extension and latest_extension.status == 'PENDING_SUPPLIER':
            return latest_extension.id
        
        return None

    def get_pending_substitution_id(self, obj):
        latest_subs = obj.substitutions.order_by('-created_at').first()
        
        if latest_subs and latest_subs.status == 'PENDING_SUPPLIER':
            return latest_subs.id
        
        return None


class ServiceOrderCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = [
            'title',
            'service_request_id',
            'winning_offer_id',
            'supplier_id',
            'start_date',
            'current_end_date',
            'supplier_name',
            'current_specialist_id',
            'current_specialist_name',
            'role',
            'domain',
            'current_man_days',
            'daily_rate',
            'current_contract_value',
            'notes',
        ]
    
    def validate(self, data):
        if data.get('start_date') and data.get('original_end_date'):
            if data['start_date'] >= data['original_end_date']:
                raise serializers.ValidationError(
                    "Start date must be before end date"
                )
        
        return data


class ServiceOrderUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrder
        fields = [
            'status',
            'notes',
        ]


# ====================
# EXTENSION SERIALIZERS
# ====================
class ExtensionDetailSerializer(serializers.ModelSerializer):
    service_order_title = serializers.CharField(
        source='service_order.title',
        read_only=True
    )
    service_order_current_end_date = serializers.DateField(
        source='service_order.current_end_date',
        read_only=True
    )
    
    class Meta:
        model = ServiceOrderExtension
        fields = '__all__'
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class ExtensionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrderExtension
        fields = [
            'service_order',
            'additional_man_days',
            'new_end_date',
            'additional_cost',
            'reason',
        ]
    
    def validate(self, data):
        service_order = data.get('service_order')
        
        if service_order.status not in ['ACTIVE', 'PENDING_EXTENSION']:
            raise serializers.ValidationError(
                "Extension can only be requested for active service orders"
            )
        
        if data.get('new_end_date') <= service_order.current_end_date:
            raise serializers.ValidationError(
                "New end date must be after current end date"
            )
        
        expected_cost = data.get('additional_man_days') * service_order.daily_rate
        if abs(data.get('additional_cost') - expected_cost) > Decimal('0.01'):
            raise serializers.ValidationError(
                f"Additional cost should be {expected_cost} "
                f"(additional_man_days * daily_rate)"
            )
        
        return data
    
    def create(self, validated_data):
        extension = super().create(validated_data)
        service_order = extension.service_order
        service_order.status = 'PENDING_EXTENSION'
        service_order.save()
        
        return extension


# ====================
# SUBSTITUTION SERIALIZERS
# ====================
class SubstitutionDetailSerializer(serializers.ModelSerializer):
    service_order_title = serializers.CharField(
        source='service_order.title',
        read_only=True
    )
    
    class Meta:
        model = ServiceOrderSubstitution
        fields = '__all__'
        read_only_fields = [
            'id',
            'created_at',
            'updated_at',
        ]


class SubstitutionCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOrderSubstitution
        fields = [
            'service_order',
            'initiated_by',
            'outgoing_specialist_id',
            'outgoing_specialist_name',
            'incoming_specialist_id',
            'incoming_specialist_name',
            'incoming_specialist_daily_rate',
            'reason',
        ]
    
    def validate(self, data):
        service_order = data.get('service_order')
        
        if service_order.status not in ['ACTIVE', 'PENDING_SUBSTITUTION']:
            raise serializers.ValidationError(
                "Substitution can only be requested for active service orders"
            )
        
        if data.get('outgoing_specialist_id') != service_order.current_specialist_id:
            raise serializers.ValidationError(
                "Outgoing specialist must be the current specialist"
            )
        
        if data.get('incoming_specialist_id') == data.get('outgoing_specialist_id'):
            raise serializers.ValidationError(
                "Incoming specialist must be different from outgoing specialist"
            )
        
        return data
    
    def create(self, validated_data):
        if validated_data['initiated_by'] == 'PROJECT_MANAGER':
            validated_data['status'] = 'PENDING_SUPPLIER'
        else:
            validated_data['status'] = 'PENDING_CLIENT'
        
        substitution = super().create(validated_data)
        
        service_order = substitution.service_order
        service_order.status = 'PENDING_SUBSTITUTION'
        service_order.save()
        
        return substitution
