import logging
import os
import boto3
import botocore
from botocore.exceptions import ClientError
from typing import BinaryIO, Optional, Dict, Any

from app.core.config.settings import settings

logger = logging.getLogger(__name__)


class S3Service:
    """Service for interacting with AWS S3 or S3-compatible storage"""
    
    def __init__(self):
        """Initialize S3 client"""
        self.bucket_name = settings.S3_BUCKET_NAME
        
        # Configure S3 client
        s3_kwargs = {
            "aws_access_key_id": settings.S3_ACCESS_KEY,
            "aws_secret_access_key": settings.S3_SECRET_KEY,
            "region_name": settings.S3_REGION,
        }
        
        # Add endpoint URL if provided (for MinIO or other S3-compatible storage)
        if settings.S3_ENDPOINT_URL:
            s3_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        
        # Create the client
        self.client = boto3.client("s3", **s3_kwargs)
        
    def upload_file(
        self, 
        file_data: BinaryIO, 
        object_name: str, 
        content_type: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> bool:
        """
        Upload a file to an S3 bucket
        
        Args:
            file_data: File-like object to upload
            object_name: S3 object name (key)
            content_type: The content type of the file
            metadata: Optional metadata dictionary for the object
            
        Returns:
            True if file was uploaded, else False
        """
        # Prepare extra args
        extra_args = {
            "ContentType": content_type,
        }
        
        if metadata:
            extra_args["Metadata"] = metadata
        
        try:
            self.client.upload_fileobj(
                file_data, 
                self.bucket_name, 
                object_name,
                ExtraArgs=extra_args
            )
            logger.info(f"Successfully uploaded file to {object_name}")
            return True
        except ClientError as e:
            logger.error(f"Error uploading file to S3: {e}")
            return False
    
    def download_file(self, object_name: str, file_path: str) -> bool:
        """
        Download a file from S3 bucket
        
        Args:
            object_name: S3 object name (key)
            file_path: Local file path to save the downloaded file
            
        Returns:
            True if file was downloaded, else False
        """
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            
            self.client.download_file(
                self.bucket_name,
                object_name,
                file_path
            )
            logger.info(f"Successfully downloaded {object_name} to {file_path}")
            return True
        except ClientError as e:
            logger.error(f"Error downloading file from S3: {e}")
            return False
    
    def delete_file(self, object_name: str) -> bool:
        """
        Delete a file from S3 bucket
        
        Args:
            object_name: S3 object name (key)
            
        Returns:
            True if file was deleted, else False
        """
        try:
            self.client.delete_object(
                Bucket=self.bucket_name,
                Key=object_name
            )
            logger.info(f"Successfully deleted {object_name}")
            return True
        except ClientError as e:
            logger.error(f"Error deleting file from S3: {e}")
            return False
    
    def get_file_url(self, object_name: str, expiration: int = 3600) -> Optional[str]:
        """
        Generate a presigned URL for an S3 object
        
        Args:
            object_name: S3 object name (key)
            expiration: Time in seconds for the URL to remain valid
            
        Returns:
            Presigned URL as string or None if error
        """
        try:
            response = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': object_name
                },
                ExpiresIn=expiration
            )
            return response
        except ClientError as e:
            logger.error(f"Error generating presigned URL: {e}")
            return None


# Create a singleton instance
s3_service = S3Service() 