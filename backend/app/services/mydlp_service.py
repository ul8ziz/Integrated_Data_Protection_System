"""
MyDLP service for data loss prevention and monitoring
"""
import requests
import logging
from typing import Dict, Any, List, Optional
from app.config import settings

logger = logging.getLogger(__name__)


class MyDLPService:
    """Service for integrating with MyDLP CE for data loss prevention"""
    
    def __init__(self):
        """Initialize MyDLP service"""
        self.enabled = settings.MYDLP_ENABLED
        self.api_url = settings.MYDLP_API_URL.rstrip('/')
        self.api_key = settings.MYDLP_API_KEY
        
        # Check if running on localhost
        self.is_localhost = "localhost" in self.api_url or "127.0.0.1" in self.api_url
        
        if self.enabled:
            logger.info(f"MyDLP service initialized with API URL: {self.api_url}")
            if self.is_localhost:
                logger.info("MyDLP running in localhost mode - monitoring local machine")
        else:
            logger.info("MyDLP service is disabled")
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Optional[Dict]:
        """
        Make API request to MyDLP
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint
            data: Request data
            
        Returns:
            Response data or None if error
        """
        if not self.enabled:
            logger.warning("MyDLP is disabled, skipping request")
            return None
        
        try:
            url = f"{self.api_url}{endpoint}"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}" if self.api_key else None
            }
            headers = {k: v for k, v in headers.items() if v is not None}
            
            # Increase timeout for localhost (faster)
            timeout = 5 if self.is_localhost else 10
            
            response = requests.request(
                method=method,
                url=url,
                json=data,
                headers=headers,
                timeout=timeout
            )
            
            response.raise_for_status()
            return response.json() if response.content else {}
            
        except requests.exceptions.ConnectionError as e:
            if self.is_localhost:
                # Use debug level to reduce log noise when MyDLP is not installed
                # This is expected in development/simulation mode
                logger.debug(f"MyDLP not running on localhost (simulation mode). To use real MyDLP, start the service or set MYDLP_ENABLED=false")
            else:
                logger.error(f"Error connecting to MyDLP: {e}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Error making MyDLP request: {e}")
            return None
    
    def block_data_transfer(self, source_ip: str, destination: str, 
                          detected_entities: List[Dict], reason: str = None) -> bool:
        """
        Block data transfer based on detected sensitive data
        
        Args:
            source_ip: Source IP address
            destination: Destination (IP, URL, etc.)
            detected_entities: List of detected sensitive entities
            reason: Reason for blocking
            
        Returns:
            True if blocked successfully, False otherwise
        """
        if not self.enabled:
            logger.debug("MyDLP disabled, simulating block (returning True)")
            return True
        
        try:
            data = {
                "action": "block",
                "source_ip": source_ip or "127.0.0.1",
                "destination": destination,
                "detected_entities": detected_entities,
                "reason": reason or "Sensitive data detected"
            }
            
            result = self._make_request("POST", "/api/v1/block", data)
            if result:
                logger.info(f"Data transfer blocked: {source_ip} -> {destination}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error blocking data transfer: {e}")
            return False
    
    def monitor_network_traffic(self, traffic_data: Dict) -> Dict[str, Any]:
        """
        Monitor network traffic for sensitive data
        
        Args:
            traffic_data: Traffic information (source, destination, content, etc.)
            
        Returns:
            Monitoring result with detected issues
        """
        if not self.enabled:
            return {"monitored": False, "reason": "MyDLP disabled"}
        
        # Set default source_ip to localhost if not provided
        if "source_ip" not in traffic_data:
            traffic_data["source_ip"] = "127.0.0.1"
        
        try:
            result = self._make_request("POST", "/api/v1/monitor", traffic_data)
            return result or {"monitored": False, "error": "No response"}
            
        except Exception as e:
            logger.error(f"Error monitoring network traffic: {e}")
            return {"monitored": False, "error": str(e)}
    
    def block_email(self, email_id: str, reason: str = None) -> bool:
        """
        Block email transmission
        
        Args:
            email_id: Email identifier
            reason: Reason for blocking
            
        Returns:
            True if blocked successfully, False otherwise
        """
        if not self.enabled:
            logger.info("MyDLP disabled, simulating email block")
            return True
        
        try:
            data = {
                "action": "block_email",
                "email_id": email_id,
                "reason": reason or "Sensitive data detected in email"
            }
            
            result = self._make_request("POST", "/api/v1/block-email", data)
            if result:
                logger.info(f"Email blocked: {email_id}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Error blocking email: {e}")
            return False
    
    def create_policy(self, policy_data: Dict) -> Optional[Dict]:
        """
        Create a policy in MyDLP
        
        Args:
            policy_data: Policy configuration
            
        Returns:
            Created policy data or None
        """
        if not self.enabled:
            logger.info("MyDLP disabled, policy creation skipped")
            return None
        
        try:
            result = self._make_request("POST", "/api/v1/policies", policy_data)
            return result
            
        except Exception as e:
            logger.error(f"Error creating MyDLP policy: {e}")
            return None
    
    def get_policies(self) -> List[Dict]:
        """
        Get all MyDLP policies
        
        Returns:
            List of policies
        """
        if not self.enabled:
            return []
        
        try:
            result = self._make_request("GET", "/api/v1/policies")
            return result.get("policies", []) if result else []
            
        except Exception as e:
            logger.error(f"Error getting MyDLP policies: {e}")
            return []
    
    def is_enabled(self) -> bool:
        """Check if MyDLP is enabled"""
        return self.enabled
    
    def is_local(self) -> bool:
        """Check if MyDLP is running on localhost"""
        return self.is_localhost

