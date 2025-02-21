#!/usr/bin/env python3
import http.client
import json
import ssl
import base64
import os
import argparse
import re
import time

class NutanixAPIError(Exception):
    """Custom exception for Nutanix API errors"""
    pass

class NutanixAPI:
    def __init__(self, pc_ip, username, password):
        """Initialize Nutanix API client
        
        Args:
            pc_ip: Prism Central IP address or hostname
            username: API username 
            password: API password
        """
        self.pc_ip = pc_ip
        self.username = username
        self.password = password
        
        # Create SSL context that doesn't verify cert
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def make_request(self, method, endpoint, data=None):
        """Make HTTP request to Nutanix API
        
        Args:
            method: HTTP method (GET, POST, PUT, etc)
            endpoint: API endpoint path
            data: Optional request body data
            
        Returns:
            API response as dictionary
            
        Raises:
            NutanixAPIError: If API request fails
        """
        # Setup connection
        conn = http.client.HTTPSConnection(
            self.pc_ip,
            port=9440,
            context=self.ssl_context
        )
        try:
            # Setup headers
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }
            # Add basic auth header
            auth_str = f'{self.username}:{self.password}'
            auth_bytes = auth_str.encode('ascii')
            base64_auth = base64.b64encode(auth_bytes).decode('ascii')
            headers['Authorization'] = f'Basic {base64_auth}'
            
            if data:
                body = json.dumps(data)
            else:
                body = None

            conn.request(method, f'/api/nutanix/v3/{endpoint}', body, headers)
            response = conn.getresponse()
            if not (200 <= response.status < 300):
                raise NutanixAPIError(f'API request failed with status {response.status}: {response.read().decode()}')
                
            return json.loads(response.read().decode())
            
        except Exception as e:
            raise NutanixAPIError(f'API request failed: {str(e)}')
        finally:
            conn.close()

    def get_vm_details(self, vm_uuid):
        """Get VM details by UUID
        
        Args:
            vm_uuid: UUID of the VM to get details for
            
        Returns:
            VM details as dictionary
        """
        return self.make_request('GET', f'vms/{vm_uuid}')

    def list_vms(self):
        """List all VMs
        
        Returns:
            List of VMs
        """
        response = self.make_request('POST', 'vms/list', {'kind': 'vm'})
        return response.get('entities', [])
    
    def update_vm(self, vm_uuid, vm_spec):
        """Update VM configuration
        
        Args:
            vm_uuid: UUID of the VM to update
            vm_spec: Complete VM specification to update
            
        Returns:
            Update task details
        """
        return self.make_request('PUT', f'vms/{vm_uuid}', vm_spec)

    def get_task_status(self, task_uuid):
        """Get the status of a task
        
        Args:
            task_uuid: UUID of the task to check
            
        Returns:
            Task status details
        """
        return self.make_request('GET', f'tasks/{task_uuid}')

    def wait_for_task(self, task_uuid, timeout_secs=300, interval_secs=5):
        """Wait for a task to complete
        
        Args:
            task_uuid: UUID of the task to monitor
            timeout_secs: Maximum time to wait in seconds (default: 300)
            interval_secs: Time between status checks in seconds (default: 5)
            
        Returns:
            Final task status
            
        Raises:
            NutanixAPIError: If task fails or times out
        """
        start_time = time.time()
        
        while True:
            task_status = self.get_task_status(task_uuid)
            current_status = task_status.get('status', {})
            state = current_status.get('state', '')
            
            # Check if task completed
            if state == 'SUCCEEDED':
                return task_status
            elif state == 'FAILED':
                error_detail = current_status.get('error_detail', 'No error details available')
                raise NutanixAPIError(f'Task failed: {error_detail}')
            
            # Check if we've exceeded timeout
            if time.time() - start_time > timeout_secs:
                raise NutanixAPIError(f'Task monitoring timed out after {timeout_secs} seconds')
            
            # Wait before checking again
            time.sleep(interval_secs)

def find_vm_by_name(nutanix, vm_name):
    """
    Find VM by name (case-insensitive)
    
    Args:
        nutanix: NutanixAPI instance
        vm_name: Name of VM to find
        
    Returns:
        Tuple of (VM UUID, VM name) if found, (None, None) otherwise
    """
    # Retrieve all VMs and match by name
    vms = nutanix.list_vms()
    pattern = re.compile(re.escape(vm_name), re.IGNORECASE)
    for vm in vms:
        current_name = vm.get('spec', {}).get('name', '')
        current_uuid = vm.get('metadata', {}).get('uuid', '')
        if pattern.search(current_name):
            return current_uuid, current_name
    
    return None, None

def update_vsensor(nutanix, vm_uuid):
    """Update vSensor VM with network function provider category
    
    Args:
        nutanix: NutanixAPI instance
        vm_uuid: UUID of vSensor VM to update
        
    Returns:
        Task status after completion
    """
    # Step 8.3 - Get current VM spec
    vm_details = nutanix.get_vm_details(vm_uuid)
    
    # Add network function provider category
    if 'categories' not in vm_details['metadata']:
        vm_details['metadata']['categories'] = {}
    
    # Step 8.4 - Add category provider value
    provider_value = 'vectra_ai'
    vm_details['metadata']['categories']['network_function_provider'] = provider_value
    
    # Update VM with new spec
    result = nutanix.update_vm(vm_uuid, vm_details)
    
    # Get task UUID and monitor until completion
    if result.get('status', {}).get('state') == 'PENDING':
        task_uuid = result['status']['execution_context']['task_uuid']
        return nutanix.wait_for_task(task_uuid)
    
    return result

def main(prism_central_ip, prism_central_username, prism_central_password, vm_name):
    try:
        # Initialize API client
        nutanix = NutanixAPI(prism_central_ip, prism_central_username, prism_central_password)

        # Step 8.2 - Find VM by name and return UUID
        print(f'Looking for VM with name: {vm_name}')
        vm_uuid, found_name = find_vm_by_name(nutanix, vm_name)
        if not vm_uuid:
            raise NutanixAPIError(f'VM with name {vm_name} not found')
        
        print(f'Found VM: {found_name} (UUID: {vm_uuid})')

        # Update vSensor VM
        print('Updating vSensor VM with provider value vectra_ai...')
        update_vsensor(nutanix, vm_uuid)
        
        print('Update completed successfully')

    except NutanixAPIError as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

def test(prism_central_ip, prism_central_username, prism_central_password, vm_name):
    try:
        # Initialize API client
        nutanix = NutanixAPI(prism_central_ip, prism_central_username, prism_central_password)
        
        # Find VM by name
        print(f'Looking for VM with name: {vm_name}')
        vm_uuid, found_name = find_vm_by_name(nutanix, vm_name)
        if vm_uuid:
            print(f'Found VM: {found_name} (UUID: {vm_uuid})')
        else:
            print(f'No VM found matching name: {vm_name}')

    except NutanixAPIError as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Update Nutanix vSensor VM Configuration')
    parser.add_argument('--vm-name', required=True, help='Name of the vSensor VM to update')
    parser.add_argument('--test', action='store_true', help='Run in test mode')
    args = parser.parse_args()

    PC_IP = os.getenv('PC_IP', 'prism')
    USERNAME = os.getenv('PC_USERNAME', 'admin')
    PASSWORD = os.getenv('PC_PASSWORD', 'Nutanix/123')
    
    print(f'Connecting to {PC_IP} as {USERNAME}...')
    if args.test:
        test(PC_IP, USERNAME, PASSWORD, args.vm_name)
    else:
        main(PC_IP, USERNAME, PASSWORD, args.vm_name)
