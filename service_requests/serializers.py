from rest_framework import serializers
from .models import ServiceRequest, ServiceOffer


class ServiceRequestSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceRequest
        fields = "__all__"
        read_only_fields = [
            "id",
            "process_id",
            "created_at",
            "updated_at",
        ]

    def validate_criteria_json(self, value):
        """
        Validate criteria_json field structure
        """
        # Allow empty dict
        if not value or value == {}:
            return value
        
        # Check if all required keys are present
        required_keys = {'skills', 'certifications', 'languages'}
        
        # Check exact keys
        if set(value.keys()) != required_keys:
            raise serializers.ValidationError(
                f"criteria_json must contain exactly these keys: {required_keys}"
            )
        
        # Validate all values are lists of strings
        for key, val in value.items():
            if not isinstance(val, list) or not all(isinstance(i, str) for i in val):
                raise serializers.ValidationError(
                    f"'{key}' must be a list of strings"
                )
        
        return value
    

class ServiceOfferSerializer(serializers.ModelSerializer):
    class Meta:
        model = ServiceOffer
        fields = "__all__"
        read_only_fields = [
            "id",
            "created_at",
            "updated_at",
        ]