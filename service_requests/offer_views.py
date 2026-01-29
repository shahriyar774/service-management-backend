import requests
from rest_framework import viewsets, mixins, status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.decorators import action
from django.conf import settings

from .models import *
from .serializers import ServiceOfferSerializer
from service_orders.models import ServiceOrder
from flowable_client import *


class ServiceOfferViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    queryset = ServiceOffer.objects.order_by("-created_at")
    serializer_class = ServiceOfferSerializer
    permission_classes = [AllowAny,]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        offer = serializer.save()
        
        try:
            # Step 1: Find ALL executions for this process instance
            executions_url = f"{settings.FLOWABLE_BASE_URL}/runtime/executions"
            params = {
                'processInstanceId': offer.service_request.process_id
            }
            
            exec_response = requests.get(
                executions_url,
                params=params,
                auth=settings.FLOWABLE_AUTH
            )
            print('called execution get request............')

            if exec_response.status_code != 200:
                return Response({
                    'success': False,
                    'error': 'Failed to find executions'
                }, status=400)
            
            executions = exec_response.json().get('data', [])
            
            print('got execution data.....and will look for wait Trigger')

            # Step 2: Find the execution waiting at the message event
            waiting_execution = None
            for execution in executions:
                if execution.get('activityId') == 'waitForApiTrigger':
                    waiting_execution = execution
                    break

            if not waiting_execution:
                return Response({
                    'success': False,
                    'error': 'No execution found waiting at message event',
                    'availableExecutions': executions
                }, status=404)
            
            print('got wait Trigger...........and will trigger msg envt')
            
            execution_id = waiting_execution['id']

            # Step 3: Trigger the message event on the CORRECT execution
            trigger_url = f"{settings.FLOWABLE_BASE_URL}/runtime/executions/{execution_id}"
            payload = {
                "action": "messageEventReceived",
                "messageName": "ApiTriggerMessage",
                "variables": [
                    {
                        "name": "offerId",
                        "value": str(offer.id)
                    }
                ]
            }
            
            trigger_response = requests.put(
                trigger_url,
                json=payload,
                headers={'Content-Type': 'application/json'},
                auth=settings.FLOWABLE_AUTH
            )

            print('triggered msg envt....')
            
            if trigger_response.status_code in [200, 201]:
                return Response({
                    'success': True,
                    'message': 'Offer submitted and Message event triggered successfully',
                    'executionId': execution_id,
                    'processInstanceId': offer.service_request.process_id,
                })
            else:
                return Response({
                    'success': False,
                    'error': trigger_response.text,
                    'statusCode': trigger_response.status_code
                }, status=trigger_response.status_code)
                
        except Exception as e:
            return Response({
                'success': False,
                'error': str(e)
            }, status=500)
    

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
                offer_id = task['variables'].get('offerId')
                
                if not offer_id:
                    continue
                
                try:
                    # Get contract from database
                    offer = ServiceOffer.objects.get(id=offer_id)
                    
                    task_data = {
                        'task_id': task['task_id'],
                        'task_name': task['task_name'],
                        'created_time': task['created_time'],
                        'offer': {
                            'id': offer.id,
                            'provider_name': offer.provider_name,
                            'specialist_name': offer.specialist_name,
                            'status': offer.status,
                            'daily_rate': offer.daily_rate,
                            'travel_cost': offer.travel_cost,
                            'total_cost': offer.total_cost,
                        }
                    }
                    
                    tasks_with_request.append(task_data)
                    
                except ServiceOffer.DoesNotExist:
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
        
        offer_id = task_info['variables'].get('offerId')

        if not offer_id:
            return Response(
                {"error": "Task does not have offer id"},
                status=status.HTTP_404_NOT_FOUND
            )
        
        try:
            offer = ServiceOffer.objects.get(id=offer_id)
        except ServiceOffer.DoesNotExist:
            return Response(
                {"error": "Service offer not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # generate service request in 3rd party app
        if decision == "final_approval":
            offer_status = "ACCEPTED"
        elif decision == "final_rejection":
            offer_status = "REJECTED"
        else:
            offer_status = "UNDER_REVIEW"

        offer.status = offer_status
        offer.save()

        try:
            third_party_api_url = f"{settings.THIRD_PARTY_API_BASE}/requests/service-offers/update-status/"
            payload = {
                "id": str(offer.external_id) ,
                "status": offer_status
            }
            response = call_third_party_api(url=third_party_api_url, payload=payload)

        except Exception as e:
            print(f"Failed to call 3rd party API: {str(e)}")
            raise Exception(f"Failed to update 3rd party API: {str(e)}")
        
        # Step 1: Complete Flowable task
        try:
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

        # create service order
        if offer.status == 'ACCEPTED' or decision == "final_approval":
            ServiceOrder.objects.create(
                title=offer.service_request.title,
                service_request_id=str(offer.service_request.id),
                winning_offer_id=str(offer.id),
                supplier_id=offer.provider_id,
                start_date=offer.service_request.start_date,
                current_end_date=offer.service_request.end_date,
                original_end_date=offer.service_request.end_date,
                supplier_name=offer.provider_name,
                current_specialist_id=offer.specialist_id,
                current_specialist_name=offer.specialist_name,
                original_specialist_id=offer.specialist_id,
                original_specialist_name=offer.specialist_name,
                role=offer.service_request.role_name,
                current_man_days=offer.service_request.expected_man_days,
                original_man_days=offer.service_request.expected_man_days,
                daily_rate=offer.daily_rate,
                original_contract_value=offer.total_cost,
                current_contract_value=offer.total_cost,
            )

            try:
                project_req = ProjectRequest.objects.order_by('created_at').first()
                if project_req:
                    project_req.specialist_id = offer.specialist_id
                    project_req.save()
            except:
                pass
        
        return Response({
            'message': f'Initial validation {decision} successfully',
        }, status=status.HTTP_200_OK)
