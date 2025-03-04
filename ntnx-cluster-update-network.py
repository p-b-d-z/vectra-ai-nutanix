#!/usr/bin/env python3
import http.client
import json
import ssl
import base64
import os
import argparse
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

    def list_networks(self, offset=0, length=500):
        """List networks with pagination support
        
        Args:
            offset: Starting offset for results (default: 0)
            length: Maximum number of results to return (default: 500)
            
        Returns:
            List of networks
        """
        params = {
            'kind': 'subnet',
            'offset': offset,
            'length': length
        }
        response = self.make_request('POST', 'subnets/list', params)
        return response.get('entities', [])

    def get_network_details(self, network_uuid):
        """Get network details by UUID
        
        Args:
            network_uuid: UUID of the network to get details for
            
        Returns:
            Network details as dictionary
        """
        return self.make_request('GET', f'subnets/{network_uuid}')

    def find_network_by_vlan(self, vlan_id, offset=0, length=500):
        """Find network by VLAN ID
        
        Args:
            vlan_id: VLAN ID to search for
            offset: Starting offset for results (default: 0)
            length: Maximum number of results to return (default: 500)
            
        Returns:
            Network entity if found, None otherwise
        """
        networks = self.list_networks(offset, length)
        for network in networks:
            if network.get('spec', {}).get('resources', {}).get('vlan_id') == vlan_id:
                return network
        return None

    def update_subnet(self, subnet_uuid, subnet_spec):
        """Update subnet configuration
        
        Args:
            subnet_uuid: UUID of the subnet to update
            subnet_spec: Complete subnet specification to update
            
        Returns:
            Update task details
        """
        return self.make_request('PUT', f'subnets/{subnet_uuid}', subnet_spec)

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
            state = task_status.get('status', '')
            
            # Check if task completed
            if state == 'SUCCEEDED':
                return task_status
            elif state == 'FAILED':
                error_detail = task_status.get('error_detail', 'No error details available')
                raise NutanixAPIError(f'Task failed: {error_detail}')
            
            # Check if we've exceeded timeout
            if time.time() - start_time > timeout_secs:
                raise NutanixAPIError(f'Task monitoring timed out after {timeout_secs} seconds')
            
            # Wait before checking again
            time.sleep(interval_secs)

    def list_network_function_chains(self):
        """List network function chains
        
        Returns:
            List of network function chains
        """
        params = {
            'kind': 'network_function_chain'
        }
        response = self.make_request('POST', 'network_function_chains/list', params)
        return response.get('entities', [])

def update_network(nutanix, vlan_id, chain_uuid=None):
    """Update network with network function chain reference based on VLAN ID
    
    Args:
        nutanix: NutanixAPI instance
        vlan_id: VLAN ID to search for
        chain_uuid: UUID of the network function chain to use
        
    Returns:
        Task status after completion
    """
    
    # Find network by VLAN ID
    network = nutanix.find_network_by_vlan(vlan_id)
    if not network:
        raise NutanixAPIError(f'Network with VLAN ID {vlan_id} not found')
    
    # Get network UUID
    network_uuid = network.get('metadata', {}).get('uuid')
    if not network_uuid:
        raise NutanixAPIError('Network UUID not found in metadata')
    
    # Create a minimal update spec with just metadata and spec
    update_spec = {
        'metadata': network.get('metadata', {}),
        'spec': network.get('spec', {})
    }
    
    # Add network function chain reference to resources
    if 'network_function_chain_reference' not in update_spec['spec']['resources']:
        if not chain_uuid:
            raise NutanixAPIError('Network function chain UUID is required')
            
        update_spec['spec']['resources'] = {
            'network_function_chain_reference': {
                'kind': 'network_function_chain',
                'name': 'vectra_tap',
                'uuid': chain_uuid
            }
        }
    
        # Update subnet with new spec
        result = nutanix.update_subnet(network_uuid, update_spec)
        # Get task UUID and monitor until completion
        if result.get('status', {}).get('state') == 'PENDING':
            task_uuid = result['status']['execution_context']['task_uuid']
            return nutanix.wait_for_task(task_uuid)
        
        return result
    else:
        print(f'Network with VLAN ID {vlan_id} already has network function chain reference')

def main(prism_central_ip, prism_central_username, prism_central_password, vlan_id):
    try:
        # Initialize API client
        nutanix = NutanixAPI(prism_central_ip, prism_central_username, prism_central_password)

        # First, get all vectra_tap network function chains by cluster
        print('Looking for vectra_tap network function chains...')
        chains = nutanix.list_network_function_chains()
        cluster_chains = {}
        
        for chain in chains:
            if chain.get('spec', {}).get('name') == 'vectra_tap':
                cluster_name = chain.get('spec', {}).get('cluster_reference', {}).get('name')
                if cluster_name:
                    chain_uuid = chain.get('metadata', {}).get('uuid')
                    if chain_uuid:
                        cluster_chains[cluster_name] = {
                            'uuid': chain_uuid,
                            'created': chain.get('metadata', {}).get('creation_time')
                        }
        
        if not cluster_chains:
            raise NutanixAPIError('No vectra_tap network function chains found in any cluster')
            
        print(f'Found vectra_tap chains in {len(cluster_chains)} cluster(s):')
        for cluster_name, chain_info in cluster_chains.items():
            print(f'\nCluster: {cluster_name}')
            print(f'  Chain UUID: {chain_info["uuid"]}')
            print(f'  Created: {chain_info["created"]}')
        print()

        # Find networks by VLAN ID
        print(f'Looking for networks with VLAN ID: {vlan_id}')
        networks = nutanix.list_networks()
        matching_networks = []
        
        for network in networks:
            if network.get('spec', {}).get('resources', {}).get('vlan_id') == vlan_id:
                cluster_name = network.get('spec', {}).get('cluster_reference', {}).get('name')
                if cluster_name in cluster_chains:
                    matching_networks.append({
                        'network': network,
                        'cluster_name': cluster_name,
                        'chain_uuid': cluster_chains[cluster_name]['uuid']
                    })
                else:
                    print(f'WARNING: Network found in cluster {cluster_name} but no matching chain exists')
                
        if not matching_networks:
            raise NutanixAPIError(f'No networks found with VLAN ID {vlan_id} in clusters with vectra_tap chains')
        
        print(f'\nFound {len(matching_networks)} network(s) with VLAN ID {vlan_id} in matching clusters')
        
        # Update each matching network
        for match in matching_networks:
            network = match['network']
            name = network.get('spec', {}).get('name')
            uuid = network.get('metadata', {}).get('uuid')
            cluster_name = match['cluster_name']
            chain_uuid = match['chain_uuid']
            
            print(f'\nProcessing network: {name}')
            print(f'  UUID: {uuid}')
            print(f'  Cluster: {cluster_name}')
            print(f'  Chain UUID: {chain_uuid}')
            
            # Get network UUID
            if not uuid:
                print(f'Skipping network {name} - UUID not found in metadata')
                continue
            
            # Create a minimal update spec with just metadata and spec
            update_spec = {
                'metadata': network.get('metadata', {}),
                'spec': network.get('spec', {})
            }
            
            # Add network function chain reference to resources
            if 'network_function_chain_reference' not in update_spec['spec'].get('resources', {}):                
                update_spec['spec']['resources']['network_function_chain_reference'] = {
                    'kind': 'network_function_chain',
                    'name': 'vectra_tap',
                    'uuid': chain_uuid
                }
            
                print(f'Updating network {name} with network function chain reference...')
                # Update subnet with new spec
                result = nutanix.update_subnet(uuid, update_spec)
                # Get task UUID and monitor until completion
                if result.get('status', {}).get('state') == 'PENDING':
                    task_uuid = result['status']['execution_context']['task_uuid']
                    nutanix.wait_for_task(task_uuid)
                
                print(f'Successfully updated network {name}')
            else:
                print(f'Network {name} already has network function chain reference - skipping')
        
        print('\nAll network updates completed successfully')

    except NutanixAPIError as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

def test(prism_central_ip, prism_central_username, prism_central_password, vlan_id):
    try:
        # Initialize API client
        nutanix = NutanixAPI(prism_central_ip, prism_central_username, prism_central_password)
        
        # First, get all vectra_tap network function chains by cluster
        print('Looking for vectra_tap network function chains...')
        chains = nutanix.list_network_function_chains()
        cluster_chains = {}
        
        for chain in chains:
            if chain.get('spec', {}).get('name') == 'vectra_tap':
                cluster_name = chain.get('spec', {}).get('cluster_reference', {}).get('name')
                if cluster_name:
                    chain_uuid = chain.get('metadata', {}).get('uuid')
                    if chain_uuid:
                        cluster_chains[cluster_name] = {
                            'uuid': chain_uuid,
                            'created': chain.get('metadata', {}).get('creation_time')
                        }
        
        if cluster_chains:
            print(f'\nFound vectra_tap chains in {len(cluster_chains)} clusters:')
            for cluster_name, chain_info in cluster_chains.items():
                print(f'\nCluster: {cluster_name}')
                print(f'  Chain UUID: {chain_info["uuid"]}')
                print(f'  Created: {chain_info["created"]}')
        else:
            print('\nWARNING: No vectra_tap network function chains found in any cluster!')
            print('The network update operation will fail without chains.\n')
        
        # List networks matching VLAN ID
        print(f'\nLooking for networks with VLAN ID: {vlan_id}')
        networks = nutanix.list_networks()
        matching_networks = []
        
        for network in networks:
            if network.get('spec', {}).get('resources', {}).get('vlan_id') == vlan_id:
                cluster_name = network.get('spec', {}).get('cluster_reference', {}).get('name')
                matching_networks.append({
                    'network': network,
                    'cluster_name': cluster_name,
                    'chain_uuid': cluster_chains.get(cluster_name, {}).get('uuid')
                })
                
        if matching_networks:
            print(f'\nFound {len(matching_networks)} network(s) with VLAN ID {vlan_id}:')
            for match in matching_networks:
                network = match['network']
                name = network.get('spec', {}).get('name')
                uuid = network.get('metadata', {}).get('uuid')
                cluster_name = match['cluster_name']
                chain_uuid = match['chain_uuid']
                has_chain = 'network_function_chain_reference' in network.get('spec', {}).get('resources', {})
                
                print(f'\nNetwork: {name}')
                print(f'  UUID: {uuid}')
                print(f'  Cluster: {cluster_name}')
                print(f'  Has chain reference: {has_chain}')
                if chain_uuid:
                    print(f'  Matching chain UUID: {chain_uuid}')
                else:
                    print(f'  WARNING: No matching chain found in cluster {cluster_name}')
        else:
            print(f'\nNo networks found with VLAN ID {vlan_id}')

    except NutanixAPIError as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='List and find Nutanix networks by VLAN ID')
    parser.add_argument('--vlan-id', required=True, type=int, help='VLAN ID to search for')
    parser.add_argument('--test', action='store_true', help='Run in test mode to list networks matching VLAN ID')
    args = parser.parse_args()

    PC_IP = os.getenv('PC_IP', 'prism')
    USERNAME = os.getenv('PC_USERNAME', 'admin')
    PASSWORD = os.getenv('PC_PASSWORD', 'Nutanix/123')
    
    print(f'Connecting to {PC_IP} as {USERNAME}...')
    if args.test:
        test(PC_IP, USERNAME, PASSWORD, args.vlan_id)
    else:
        main(PC_IP, USERNAME, PASSWORD, args.vlan_id)
