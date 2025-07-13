import asyncio
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
import aiohttp
from pydantic import BaseModel

from app.core.config.settings import settings
from app.core.exceptions import TaskNotFoundError

logger = logging.getLogger(__name__)

class RAGParserRequest(BaseModel):
    """Request model for RAGParser upload endpoint"""
    url: str
    options: Optional[Dict[str, Any]] = None
    callback_url: Optional[str] = None
    callback_payload: Optional[Dict[str, Any]] = None

class RAGParserResponse(BaseModel):
    """Response model from RAGParser upload endpoint"""
    task_id: str
    queue_position: int
    estimated_time: Optional[int] = None

class DocumentInfo(BaseModel):
    """Document information from RAGParser"""
    table_count: int
    image_count: int
    text_length: int
    word_count: int
    is_scanned: bool
    language: str
    rotated_pages: List[int]
    mime_type: str
    pages_processed: Optional[int] = None

class RAGParserStatusResponse(BaseModel):
    """Status response from RAGParser with complete format"""
    state: str  # "waiting", "running", "completed", "failed"
    progress: float
    result_key: Optional[str] = None
    table_keys: Optional[List[str]] = None
    started_at: Optional[str] = None  # ISO datetime string
    completed_at: Optional[str] = None  # ISO datetime string
    failed_at: Optional[str] = None  # ISO datetime string
    parser_used: Optional[str] = None
    pages_processed: Optional[int] = None
    document_info: Optional[DocumentInfo] = None
    error: Optional[str] = None

class RAGParserClient:
    """Client for communicating with the RAGParser microservice"""
    
    def __init__(self, base_url: Optional[str] = None):
        self.base_url = base_url or settings.RAGPARSER_BASE_URL
        self.bucket_url = settings.RAGPARSER_BUCKET_URL
        self.timeout = aiohttp.ClientTimeout(total=settings.RAGPARSER_TIMEOUT)
        self.api_key = settings.RAGPARSER_API_KEY
    
    async def submit_document_for_parsing(
        self, 
        document_url: str, 
        options: Optional[Dict[str, Any]] = None,
        callback_url: Optional[str] = None,
        callback_payload: Optional[Dict[str, Any]] = None
    ) -> RAGParserResponse:
        """
        Submit a document URL to RAGParser for processing
        
        Args:
            document_url: URL to the document (e.g., S3 presigned URL)
            options: Optional processing parameters
            callback_url: Optional URL for RAGParser to call upon completion
            callback_payload: Optional payload to include in the callback
            
        Returns:
            RAGParserResponse with task_id and queue information
            
        Raises:
            Exception: If the request fails
        """
        request_data = RAGParserRequest(
            url=document_url,
            options=options or {},
            callback_url=callback_url,
            callback_payload=callback_payload
        )
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                headers = {
                    "Content-Type": "application/json",
                    "X-Request-ID": f"ragpilot-{datetime.now().isoformat()}"
                }
                
                # Add API key if configured
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    
                async with session.post(
                    f"{self.base_url}/upload",
                    json=request_data.dict(),
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return RAGParserResponse(**data)
                    else:
                        error_text = await response.text()
                        raise Exception(f"RAGParser request failed: {response.status} - {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Failed to connect to RAGParser: {e}")
                raise Exception(f"Failed to connect to RAGParser service: {e}")
    
    # async def get_task_status(self, task_id: str) -> RAGParserStatus:
    #     """
    #     Get the status of a parsing task (backward compatibility method)
        
    #     Args:
    #         task_id: The task ID returned from submit_document_for_parsing
            
    #     Returns:
    #         RAGParserStatus with current status and progress
            
    #     Raises:
    #         Exception: If the request fails
    #     """
    #     # Get the new format status
    #     new_status = await self.get_task_status_new(task_id)
        
    #     # Convert to legacy format
    #     legacy_status = RAGParserStatus(
    #         task_id=task_id,
    #         status=self._convert_state_to_status(new_status.state),
    #         progress=new_status.progress,
    #         result_url=new_status.result_key,  # For backward compatibility
    #         error_message=new_status.error
    #     )
        
    #     return legacy_status
    
    async def get_task_status_new(self, task_id: str) -> RAGParserStatusResponse:
        """
        Get the status of a parsing task with new JSON format
        
        Args:
            task_id: The task ID returned from submit_document_for_parsing
            
        Returns:
            RAGParserStatusResponse with current state, progress, result_key, etc.
            
        Raises:
            Exception: If the request fails
        """
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                headers = {}
                if self.api_key:
                    headers["Authorization"] = f"Bearer {self.api_key}"
                    
                async with session.get(
                    f"{self.base_url}/status/{task_id}",
                    headers=headers
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return RAGParserStatusResponse(**data)
                    elif response.status == 404:
                        raise TaskNotFoundError(task_id)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Status request failed: {response.status} - {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Failed to get task status from RAGParser: {e}")
                raise Exception(f"Failed to get task status: {e}")
    
    async def get_parsed_result(self, result_key: str) -> Dict[str, Any]:
        """
        Download the parsed result from RAGParser's S3 bucket using result_key
        
        Args:
            result_key: S3 key to the parsed result (e.g., "results/hash/filename.json")
            
        Returns:
            Dict containing the parsed document data
            
        Raises:
            Exception: If the download fails
        """
        # Construct the full URL to the result using bucket URL
        # Handle cases where result_key already contains "results/" prefix
        if result_key.startswith("results/"):
            result_url = f"{self.bucket_url}/{result_key}"
        else:
            result_url = f"{self.bucket_url}/results/{result_key}"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                headers = {}
                # Note: Bucket URLs typically don't need API key authentication
                # if self.api_key:
                #     headers["Authorization"] = f"Bearer {self.api_key}"
                    
                async with session.get(result_url, headers=headers) as response:
                    if response.status == 200:
                        # Handle bucket storage that might serve JSON with wrong MIME type
                        try:
                            return await response.json()
                        except Exception:
                            # Fallback: get as text and parse manually
                            import json
                            text_content = await response.text()
                            return json.loads(text_content)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to download result: {response.status} - {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Failed to download parsed result: {e}")
                raise Exception(f"Failed to download parsed result: {e}")
    
    async def get_table_result(self, table_key: str) -> Dict[str, Any]:
        """
        Download a specific table result from RAGParser's S3 bucket
        
        Args:
            table_key: S3 key to the table result (e.g., "tables/hash/table_0.json")
            
        Returns:
            Dict containing the table data
            
        Raises:
            Exception: If the download fails
        """
        # Construct the full URL to the table result using bucket URL
        # Handle cases where table_key already contains "results/" prefix
        if table_key.startswith("results/"):
            table_url = f"{self.bucket_url}/{table_key}"
        else:
            table_url = f"{self.bucket_url}/results/{table_key}"
        
        async with aiohttp.ClientSession(timeout=self.timeout) as session:
            try:
                headers = {}
                # Note: Bucket URLs typically don't need API key authentication
                # if self.api_key:
                #     headers["Authorization"] = f"Bearer {self.api_key}"
                    
                async with session.get(table_url, headers=headers) as response:
                    if response.status == 200:
                        # Handle bucket storage that might serve JSON with wrong MIME type
                        try:
                            return await response.json()
                        except Exception:
                            # Fallback: get as text and parse manually
                            import json
                            text_content = await response.text()
                            return json.loads(text_content)
                    else:
                        error_text = await response.text()
                        raise Exception(f"Failed to download table result: {response.status} - {error_text}")
                        
            except aiohttp.ClientError as e:
                logger.error(f"Failed to download table result: {e}")
                raise Exception(f"Failed to download table result: {e}")
    
    def _convert_state_to_status(self, state: str) -> str:
        """Convert new state format to legacy status format"""
        state_mapping = {
            "pending": "waiting",
            "processing": "running", 
            "succeeded": "completed",
            "failed": "failed"
        }
        return state_mapping.get(state, state)

# Global client instance
ragparser_client = RAGParserClient()