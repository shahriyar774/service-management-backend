from django.db import models
from django.core.validators import MinValueValidator
from datetime import date
import uuid


class ServiceOrder(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Active'),
        ('COMPLETED', 'Completed'),
        ('CANCELLED', 'Cancelled'),
        ('SUSPENDED', 'Suspended'),
        ('PENDING_EXTENSION', 'Pending Extension'),
        ('PENDING_SUBSTITUTION', 'Pending Substitution'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    service_request_id = models.CharField(max_length=64)
    winning_offer_id = models.CharField(max_length=64)
    supplier_id = models.CharField(max_length=64)

    title = models.CharField(max_length=255)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default="ACTIVE")

    start_date = models.DateField(null=True, blank=True)
    original_end_date = models.DateField(null=True, blank=True)
    current_end_date = models.DateField(null=True, blank=True)
    actual_end_date = models.DateField(null=True, blank=True)

    supplier_name = models.CharField(max_length=30)
    current_specialist_id = models.CharField(max_length=50)
    current_specialist_name = models.CharField(max_length=255)
    original_specialist_id = models.CharField(max_length=50)
    original_specialist_name = models.CharField(max_length=255)
    
    role = models.CharField(max_length=100)
    domain = models.CharField(max_length=100, blank=True)
    
    original_man_days = models.IntegerField(validators=[MinValueValidator(1)])
    current_man_days = models.IntegerField(validators=[MinValueValidator(1)])
    
    daily_rate = models.DecimalField(max_digits=10, decimal_places=2)
    original_contract_value = models.DecimalField(max_digits=10, decimal_places=2)
    current_contract_value = models.DecimalField(max_digits=10, decimal_places=2)

    notes = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.title}"
    
    @property
    def is_active(self):
        return self.status == 'ACTIVE'
    
    @property
    def consumed_man_days(self) -> int:
        if not self.start_date or not self.current_end_date or not self.current_man_days:
            return 0

        # If start date is in the future, nothing consumed yet
        today = date.today()
        if today < self.start_date:
            return 0

        # If we're past the end date, all man days are consumed
        if today >= self.current_end_date:
            return self.current_man_days

        # Calculate the proportion of time elapsed
        total_days = (self.current_end_date - self.start_date).days
        
        # Avoid division by zero
        if total_days <= 0:
            return 0

        elapsed_days = (today - self.start_date).days
        
        # Calculate consumed man days proportionally
        consumed = int((elapsed_days / total_days) * self.current_man_days)
        
        return consumed

    @property
    def remaining_man_days(self) -> int:
        if not self.current_man_days:
            return 0
        return max(0, self.current_man_days - self.consumed_man_days)
    
    @property
    def has_been_extended(self):
        return self.current_end_date > self.original_end_date
    
    @property
    def has_been_substituted(self):
        return self.current_specialist_id != self.original_specialist_id
    
    def can_request_extension(self):
        # return self.status == 'ACTIVE' and self.remaining_man_days < 20
        return self.status == 'ACTIVE'
    
    def can_request_substitution(self):
        return self.status in ['ACTIVE', 'PENDING_SUBSTITUTION']


class ServiceOrderExtension(models.Model):
    STATUS_CHOICES = [
        ('PENDING_SUPPLIER', 'Pending Supplier Approval'),
        ('PENDING_CLIENT', 'Pending Client Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='extensions')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING_SUPPLIER')
    additional_man_days = models.IntegerField(validators=[MinValueValidator(1)])
    new_end_date = models.DateField()
    additional_cost = models.DecimalField(max_digits=12, decimal_places=2)
    reason = models.TextField()
    rejection_reason = models.TextField(blank=True)
    
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def approve(self):
        self.status = 'APPROVED'
        self._apply_extension()
        self.save()
    
    def reject(self, reason):
        self.rejection_reason = reason
        self.status = 'REJECTED'
        self.save()
        service_order = self.service_order
        service_order.status = 'ACTIVE'
        service_order.save()
    
    def _apply_extension(self):
        service_order = self.service_order
        service_order.current_end_date = self.new_end_date
        service_order.current_man_days += self.additional_man_days
        service_order.current_contract_value += self.additional_cost
        service_order.status = 'ACTIVE'
        service_order.save()


class ServiceOrderSubstitution(models.Model):
    STATUS_CHOICES = [
        ('PENDING_SUPPLIER', 'Pending Supplier Approval'),
        ('PENDING_CLIENT', 'Pending Client Approval'),
        ('APPROVED', 'Approved'),
        ('REJECTED', 'Rejected'),
        ('CANCELLED', 'Cancelled'),
    ]
    
    INITIATOR_CHOICES = [
        ('PROJECT_MANAGER', 'Project Manager (Client)'),
        ('SUPPLIER_REPRESENTATIVE', 'Supplier Representative'),
    ]
    
    REASON_CHOICES = [
        ('LOW_PERFORMANCE', 'Low Performance'),
        ('JOB_CHANGE', 'Specialist Job Change'),
        ('HEALTH_ISSUES', 'Health Issues'),
        ('PERSONAL_REASONS', 'Personal Reasons'),
        ('SKILL_MISMATCH', 'Skill Mismatch'),
        ('CLIENT_REQUEST', 'Client Request'),
        ('OTHER', 'Other'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    service_order = models.ForeignKey(ServiceOrder, on_delete=models.CASCADE, related_name='substitutions')
    initiated_by = models.CharField(max_length=30, choices=INITIATOR_CHOICES)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='PENDING_SUPPLIER')
    
    # Current Specialist (being replaced)
    outgoing_specialist_id = models.CharField(max_length=50)
    outgoing_specialist_name = models.CharField(max_length=255)
    
    # Replacement Specialist
    incoming_specialist_id = models.CharField(max_length=50, blank=True)
    incoming_specialist_name = models.CharField(max_length=255, blank=True)
    incoming_specialist_daily_rate = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    
    # Reason for substitution
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    rejection_reason = models.TextField(blank=True)
    
    created_at   = models.DateTimeField(auto_now_add=True)
    updated_at   = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def reject(self, reason):
        self.rejection_reason = reason
        self.status = 'REJECTED'
        self.save()
        
        service_order = self.service_order
        service_order.status = 'ACTIVE'
        service_order.save()
