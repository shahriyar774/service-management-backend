from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.utils import timezone

from .models import *
from .serializers import *


# ====================
# SERVICE ORDER VIEWSET
# ====================
class ServiceOrderViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrder.objects.all()
    permission_classes = [AllowAny]
    
    # Filterable fields
    filterset_fields = [
        'status',
        'supplier_name',
        'current_specialist_name',
        'role',
        'domain',
    ]
    
    # Searchable fields
    search_fields = [
        'id',
        'title',
        'current_specialist_name',
        'supplier_name',
    ]
    
    # Ordering
    ordering_fields = ['start_date', 'current_end_date', 'created_at']
    ordering = ['-created_at']

    def get_queryset(self):
        qs = self.queryset
        supplier_id = self.request.query_params.get("supplier_id")
        if supplier_id:
            qs = qs.filter(supplier_id=supplier_id)
        return qs
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ServiceOrderCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return ServiceOrderUpdateSerializer
        return ServiceOrderDetailSerializer
    
    def perform_create(self, serializer):
        validated_data = serializer.validated_data
        service_order = serializer.save(
            original_end_date=validated_data['current_end_date'],
            original_specialist_id=validated_data['current_specialist_id'],
            original_specialist_name=validated_data['current_specialist_name'],
            original_man_days=validated_data['current_man_days'],
            original_contract_value=validated_data['current_contract_value'],
        )
    
    @action(detail=True, methods=['get'])
    def extensions(self, request, pk=None):
        service_order = self.get_object()
        extensions = service_order.extensions.all()
        serializer = ExtensionDetailSerializer(extensions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def substitutions(self, request, pk=None):
        service_order = self.get_object()
        substitutions = service_order.substitutions.all()
        serializer = SubstitutionDetailSerializer(substitutions, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        service_order = self.get_object()
        
        if service_order.status != 'ACTIVE':
            return Response(
                {'error': 'Only active service orders can be completed'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        service_order.status = 'COMPLETED'
        service_order.actual_end_date = timezone.now().date()
        service_order.save()
        serializer = self.get_serializer(service_order)
        return Response(serializer.data)


# ====================
# EXTENSION VIEWSET
# ====================

class ServiceOrderExtensionViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrderExtension.objects.all()
    permission_classes = [AllowAny]
    
    # Filterable fields
    filterset_fields = ['status', 'initiated_by', 'service_order']
    
    # Ordering
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ExtensionCreateSerializer
        return ExtensionDetailSerializer
    
    @action(detail=True, methods=['post'])
    def approve_extension(self, request, pk=None):
        extension = self.get_object()
        data = request.data
        user_role = data.get('user_role', None)
        print('user role......................', user_role)

        if not user_role or user_role != "SUPPLIER_REP":
            return Response(
                {'error': 'Only Supplier Representative can approve extension'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        print("extension status -----------------------", extension.status)
        if extension.status not in ['PENDING_SUPPLIER']:
            return Response(
                {'error': 'Extension is not pending supplier approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve the extension
        extension.approve()
        
        response_serializer = ExtensionDetailSerializer(extension)
        return Response(response_serializer.data)
    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        extension = self.get_object()
        data = request.data 
        user_role = data.get('user_role', None)
        reason = data.get('reason', None)
        
        if not user_role or user_role != "SUPPLIER_REP":
            return Response(
                {'error': 'Only Supplier Representative can reject extension'},
                status=status.HTTP_400_FORBIDDEN
            )

        if not reason:
            return Response(
                {'error': 'Rejection reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if extension.status not in ['PENDING_SUPPLIER', 'PENDING_CLIENT']:
            return Response(
                {'error': 'Extension is not pending approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reject the extension
        extension.reject(reason=reason)
        
        response_serializer = ExtensionDetailSerializer(extension)
        return Response(response_serializer.data)


# ====================
# SUBSTITUTION VIEWSET
# ====================

class ServiceOrderSubstitutionViewSet(viewsets.ModelViewSet):
    queryset = ServiceOrderSubstitution.objects.all()
    permission_classes = [AllowAny]
    
    # Filterable fields
    filterset_fields = ['status', 'initiated_by', 'service_order', 'reason']
    
    # Ordering
    ordering_fields = ['created_at']
    ordering = ['-created_at']
    
    def get_serializer_class(self):
        if self.action == 'create':
            return SubstitutionCreateSerializer
        return SubstitutionDetailSerializer

    
    @action(detail=True, methods=['post'])
    def approve_substitution(self, request, pk=None):
        substitution = self.get_object()
        data = request.data
        user_role = data.get('user_role', None)
        
        if not user_role or user_role not in ["SUPPLIER_REP", "PROJECT_MANAGER"]:
            return Response(
                {'error': 'Only Project Manager/Supplier Representative can approve substitution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if substitution.status not in ['PENDING_SUPPLIER', 'PENDING_CLIENT']:
            return Response(
                {'error': 'Substitution is not pending supplier/client approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Approve the substitution
        substitution.approve()
        
        response_serializer = SubstitutionDetailSerializer(substitution)
        return Response(response_serializer.data)

    
    @action(detail=True, methods=['post'])
    def reject(self, request, pk=None):
        substitution = self.get_object()
        data = request.data
        user_role = data.get('user_role', None)
        reason = data.get('reason', None)
        
        if not user_role or user_role not in ['SUPPLIER_REP', 'PROJECT_MANAGER']:
            return Response(
                {'error': 'Only Project Manager/Supplier Representative can reject substitution'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if not reason:
            return Response(
                {'error': 'Substitution reason is required.'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if substitution.status not in ['PENDING_SUPPLIER', 'PENDING_CLIENT']:
            return Response(
                {'error': 'Substitution is not pending approval'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Reject the substitution
        substitution.reject(reason=reason)
        
        response_serializer = SubstitutionDetailSerializer(substitution)
        return Response(response_serializer.data)