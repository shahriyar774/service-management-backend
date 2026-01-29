from django.db.models import Count
from django.conf import settings
from rest_framework import viewsets, mixins, status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response

from .models import ServiceRequest
from .serializers import ServiceRequestSerializer
from flowable_client import *


class ServiceRequestViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    """
    Service Request API.
    """

    queryset = ServiceRequest.objects.all()
    serializer_class = ServiceRequestSerializer
    permission_classes = [AllowAny,]

    def get_queryset(self):
        qs = (
            ServiceRequest.objects
            .order_by("-created_at")
        )

        status_param = self.request.query_params.get("status")
        if status_param:
            qs = qs.filter(status=status_param)

        return qs


    def create(self, request):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        service_request = serializer.save()

        try:
            flowable_result = generate_request_task(request_id=str(service_request.id))

            service_request.process_id = flowable_result['id']
            service_request.save()
            
            return Response({
                'message': 'Service Request and Task generated',
                'service_request_id': str(service_request.id),
                'status': service_request.status
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to generate request: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['get'], url_path='tasks')
    def get_tasks(self, request):
        group_id = request.query_params.get('group', None)

        if not group_id:
            return Response({
                'count': 0,
                'tasks': []
            }, status=status.HTTP_200_OK)
        
        try:
            # Step 1: Get tasks from Flowable
            flowable_tasks = get_tasks_by_group(group_id=group_id)
            
            # Step 2: Enrich with contract details from local database
            tasks_with_request = []
            
            for task in flowable_tasks:
                request_id = task['variables'].get('request_id')
                
                if not request_id:
                    continue
                
                try:
                    # Get contract from database
                    service_request = ServiceRequest.objects.get(id=request_id)
                    
                    task_data = {
                        'task_id': task['task_id'],
                        'task_name': task['task_name'],
                        'created_time': task['created_time'],
                        'service_request': {
                            'id': service_request.id,
                            'title': service_request.title,
                            'role_name': service_request.role_name,
                            'technology': service_request.technology,
                            'specialization': service_request.specialization,
                            'experience_level': service_request.experience_level,
                            'start_date': service_request.start_date,
                            'end_date': service_request.end_date,
                            'expected_man_days': service_request.expected_man_days,
                            'criteria_json': service_request.criteria_json,
                            'task_description': service_request.task_description,
                            'offer_deadline': service_request.offer_deadline,
                        }
                    }
                    
                    tasks_with_request.append(task_data)
                    
                except ServiceRequest.DoesNotExist:
                    continue
                        
            return Response({
                'count': len(tasks_with_request),
                'tasks': tasks_with_request
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to retrieve tasks: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


    @action(detail=False, methods=['post'], url_path='tasks/(?P<task_id>[^/.]+)/complete')
    def complete_task(self, request, task_id=None):
        decision = request.data.get('decision', None)
        
        if not decision:
            return Response(
                {'error': f'No decision provided: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            task_info = get_task_variable(task_id=task_id)
        except Exception as e:
            return Response(
                {"error": "Task not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service_id = task_info['variables'].get('request_id')

        if not service_id:
            return Response(
                {"error": "Task does not have request id"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            service_request = ServiceRequest.objects.get(id=service_id)
        except ServiceRequest.DoesNotExist:
            return Response(
                {"error": "Service request not found"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        service_request.status = "OPEN"
        service_request.save()

        # generate service request in 3rd party app
        if decision == "approved":
            try:
                third_party_api_url = f"{settings.THIRD_PARTY_API_BASE}/requests/service-requests/generate/"
                payload = {
                    "external_id": str(service_request.id),
                    "title": service_request.title, 
                    "role_name": service_request.role_name,
                    "technology": service_request.technology,
                    "specialization": service_request.specialization,
                    "experience_level": service_request.experience_level,
                    "start_date": service_request.start_date.isoformat(),
                    "end_date": service_request.end_date.isoformat(),
                    "expected_man_days": service_request.expected_man_days,
                    "criteria_json": {
                        "skills": service_request.criteria_json.get("skills", []),
                        "certifications": service_request.criteria_json.get("certifications", []),
                        "languages": service_request.criteria_json.get("languages", [])
                    },
                    "status": service_request.status,
                    "task_description": service_request.task_description,
                    "offer_deadline": service_request.offer_deadline.isoformat(),
                    "word_mode": "Remote"
                }
                response = call_third_party_api(url=third_party_api_url, payload=payload)

            except Exception as e:
                print(f"Failed to call 3rd party API: {str(e)}")
                raise Exception(f"Failed to update 3rd party API: {str(e)}")

        try:
            print("completing task.........")
            complete_task(
                task_id=task_id,
                decision=decision
            )
        except Exception as e:
            print(f"Failed to complete task: {str(e)}")
            return Response(
                {'error': f'Failed to submit counter offer: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response({
            'message': f'Initial validation {decision} successfully',
        }, status=status.HTTP_200_OK)