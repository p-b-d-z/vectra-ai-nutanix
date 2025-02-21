import http.client
import json
import ssl
import base64
import os

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
        try:
            conn = http.client.HTTPSConnection(
                self.pc_ip,
                port=9440,
                context=self.ssl_context
            )
            
            headers = {
                'Content-Type': 'application/json',
                'Accept': 'application/json',
            }

            # Add basic auth header
            auth_str = f"{self.username}:{self.password}"
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
                raise NutanixAPIError(f"API request failed with status {response.status}: {response.read().decode()}")
                
            return json.loads(response.read().decode())
            
        except Exception as e:
            raise NutanixAPIError(f"API request failed: {str(e)}")
        finally:
            conn.close()

    def create_network_function_provider(self):
        """Create network function provider category"""
        return self.make_request(
            'PUT',
            'categories/network_function_provider',
            {'name': 'network_function_provider'}
        )

    def assign_provider_value(self, value):
        """Assign value to network function provider category"""
        return self.make_request(
            'PUT', 
            f'categories/network_function_provider/{value}',
            {'value': value}
        )

    def verify_provider_categories(self):
        """Get list of network function provider categories"""
        response = self.make_request(
            'POST',
            'categories/network_function_provider/list',
            {'kind': 'category'}
        )
        return response.get('entities', [])

    def get_clusters(self):
        """Get list of clusters"""
        response = self.make_request(
            'POST',
            'clusters/list',
            {'kind': 'cluster'}
        )
        return response.get('entities', [])

    def create_network_function_chain(self, chain_name, provider_value, cluster_name, cluster_uuid):
        """Create network function chain
        
        Args:
            chain_name: Name for the network function chain
            provider_value: Network function provider value
            cluster_name: Name of cluster to create chain in
            cluster_uuid: UUID of cluster to create chain in
        """
        chain_spec = {
            'spec': {
                'name': chain_name,
                'resources': {
                    'network_function_list': [{
                        'network_function_type': 'TAP',
                        'category_filter': {
                            'type': 'CATEGORIES_MATCH_ANY',
                            'params': {
                                'network_function_provider': [provider_value]
                            }
                        }
                    }]
                },
                'cluster_reference': {
                    'kind': 'cluster',
                    'name': cluster_name,
                    'uuid': cluster_uuid
                }
            },
            'api_version': '3.1.0',
            'metadata': {
                'kind': 'network_function_chain'
            }
        }
        return self.make_request('POST', 'network_function_chains', chain_spec)

    def verify_network_function_chains(self):
        """Get list of network function chains"""
        response = self.make_request(
            'POST',
            'network_function_chains/list',
            {'kind': 'network_function_chain'}
        )
        return response.get('entities', [])

def main(prism_central_ip, prism_central_username, prism_central_password):
    # Configuration
    provider_value = 'vectra_ai'
    chain_name = 'vectra_tap'

    try:
        # Initialize API client
        nutanix = NutanixAPI(prism_central_ip, prism_central_username, prism_central_password)

        # Step 1: Create network function provider category
        provider = nutanix.create_network_function_provider()
        print('Created network function provider category')

        # Step 2: Assign value to the category
        provider_value = nutanix.assign_provider_value(provider_value)
        print(f'Assigned value {provider_value} to network function provider')

        # Step 3: Verify category and value
        categories = nutanix.verify_provider_categories()
        print('Verified provider categories:', categories)

        # Step 4: Get cluster information
        clusters = nutanix.get_clusters()
        
        # Step 5: Create network function chain for each cluster
        for cluster in clusters:
            cluster_name = cluster['spec']['name']
            cluster_uuid = cluster['metadata']['uuid']
            print(f'Creating chain for cluster: {cluster_name} ({cluster_uuid})')
            
            chain = nutanix.create_network_function_chain(
                chain_name,
                provider_value,
                cluster_name,
                cluster_uuid
            )
            print(f'Created network function chain: {chain["metadata"]["uuid"]}')

        # Step 6: Verify chain creation
        chains = nutanix.verify_network_function_chains()
        print('Network function chains:', chains)

    except NutanixAPIError as e:
        print(f'Error: {e}')
    except Exception as e:
        print(f'Unexpected error: {e}')

if __name__ == '__main__':
    PC_IP = os.environ.get('PC_IP', 'prism')
    USERNAME = os.environ.get('PC_USERNAME', 'admin')
    PASSWORD = os.environ.get('PC_PASSWORD', 'Nutanix/123')
    main(PC_IP, USERNAME, PASSWORD)
