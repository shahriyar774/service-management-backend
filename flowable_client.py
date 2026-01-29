import requests
from django.conf import settings


print(settings.FLOWABLE_BASE_URL)

def generate_request_task(*, request_id):
    url = f"{settings.FLOWABLE_BASE_URL}/runtime/process-instances"

    payload = {
        "processDefinitionKey": "serviceRequestProcess",
        "variables": [
            {
                "name": "request_id",
                "value": request_id,
                "type": "string",
            }
        ],
    }

    response = requests.post(
        url,
        auth=settings.FLOWABLE_AUTH,
        json=payload,
        timeout=10,
    )

    response.raise_for_status()
    result = response.json()
    return response.json()


def get_tasks_by_group(*, group_id):
    """
    Get all active tasks for a specific group
    """
    url = f"{settings.FLOWABLE_BASE_URL}/runtime/tasks"
    
    params = {
        'candidateGroup': group_id,
        'includeProcessVariables': 'true'
    }
    
    try:
        response = requests.get(
            url,
            params=params,
            auth=settings.FLOWABLE_AUTH,
            timeout=10
        )
        response.raise_for_status()
        
        result = response.json()
        tasks = result.get('data', [])
        
        # Extract relevant task information
        formatted_tasks = []
        for task in tasks:
            task_info = {
                'task_id': task.get('id'),
                'task_name': task.get('name'),
                'process_instance_id': task.get('processInstanceId'),
                'created_time': task.get('createTime'),
                'assignee': task.get('assignee'),
                'variables': {}
            }
            
            # Extract process variables
            if task.get('variables'):
                for var in task.get('variables', []):
                    task_info['variables'][var.get('name')] = var.get('value')
            
            formatted_tasks.append(task_info)
        
        return formatted_tasks
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Flowable get tasks failed: {str(e)}")


def get_task_variable(*, task_id):
    """
    Get details of a specific task
    """
    url = f"{settings.FLOWABLE_BASE_URL}/runtime/tasks/{task_id}/variables"
        
    try:
        response = requests.get(
            url,
            auth=settings.FLOWABLE_AUTH,
            timeout=10
        )
        response.raise_for_status()
        
        variables = response.json()
            
        task_info = {
            'task_id': task_id,
            'variables': {}
        }

        # Extract process variables
        if variables and len(variables) > 0:
            for var in variables:
                task_info['variables'][var.get('name')] = var.get('value')
        
        return task_info
            
    except requests.exceptions.RequestException as e:
        raise Exception(f"Flowable get task failed: {str(e)}")


def complete_task(*, task_id, decision):
    """
    Complete a task with action and optional variables
    """
    url = f"{settings.FLOWABLE_BASE_URL}/runtime/tasks/{task_id}"
        
    payload = {
        "action": "complete",
        "variables": [
            {
                "name": "validationResult",
                "value": decision
            }
        ]
    }
        
    try:
        print('calling flowable ccomplete task api ...............')
        response = requests.post(
            url,
            json=payload,
            auth=settings.FLOWABLE_AUTH,
            timeout=10
        )
        print('complete task response ...............')
        print(response)
        response.raise_for_status()
        
        return True
        
    except requests.exceptions.RequestException as e:
        print('complete task excepption.................')
        raise Exception(f"Flowable task completion failed: {str(e)}")
    

def call_third_party_api(url, payload):
    headers = {
        'content-type': 'application/json'
    }

    try:
        response = requests.post(url, json=payload, headers=headers)

        if response.status_code in [200, 201]:
            return response
        else:
            print(f"API Error: {response.status_code} - {response.text}")
            raise Exception(f"API returned status {response.status_code}: {response.text}")
    
    except requests.exceptions.Timeout:
            print("Request timed out")
            raise Exception("Third party API request timed out")
        
    except requests.exceptions.ConnectionError as e:
        print(f"Connection error: {e}")
        raise Exception(f"Failed to connect to third party API: {str(e)}")
    
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        raise Exception(f"Third party API request failed: {str(e)}")