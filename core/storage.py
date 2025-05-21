from supabase import create_client, Client
from django.conf import settings
from typing import Optional, Tuple, Dict, List
import os
import mimetypes
from datetime import datetime, timedelta
import json
import uuid

class SupabaseStorage:
    """Service for handling file operations with Supabase Storage."""
    
    def __init__(self):
        """Initialize Supabase client."""
        self.client: Client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_KEY
        )
        self.bucket_name = 'media-assets'
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the media assets bucket exists."""
        try:
            self.client.storage.get_bucket(self.bucket_name)
        except Exception:
            # Create bucket if it doesn't exist
            self.client.storage.create_bucket(
                self.bucket_name,
                {'public': False}  # Private bucket for security
            )
    
    def _generate_file_path(self, file_name: str, instructor_id: int, asset_type: str) -> str:
        """Generate a unique file path for storage."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        # Sanitize filename and create path: instructor_id/asset_type/timestamp_filename
        safe_filename = ''.join(c for c in file_name if c.isalnum() or c in '._- ')
        return f"{instructor_id}/{asset_type}/{timestamp}_{safe_filename}"
    
    def _get_content_type(self, file_name: str) -> str:
        """Get the content type of a file."""
        content_type, _ = mimetypes.guess_type(file_name)
        return content_type or 'application/octet-stream'
    
    def upload_file(
        self,
        file_data: bytes,
        file_name: str,
        instructor_id: int,
        asset_type: str,
        content_type: Optional[str] = None
    ) -> Tuple[str, Dict]:
        """Upload a file to Supabase Storage.
        
        Args:
            file_data: The file data in bytes
            file_name: Original file name
            instructor_id: ID of the instructor uploading the file
            asset_type: Type of asset (image, video, audio, animation)
            content_type: Optional content type override
            
        Returns:
            Tuple of (file_path, metadata)
        """
        file_path = self._generate_file_path(file_name, instructor_id, asset_type)
        content_type = content_type or self._get_content_type(file_name)
        
        # Upload file
        self.client.storage.from_(self.bucket_name).upload(
            file_path,
            file_data,
            {'content-type': content_type}
        )
        
        # Generate signed URL for temporary access
        signed_url = self._get_signed_url(file_path)
        
        # Generate thumbnail URL for images and videos
        thumbnail_url = None
        if asset_type in ['image', 'video']:
            thumbnail_url = self._generate_thumbnail_url(file_path)
        
        metadata = {
            'file_name': file_name,
            'content_type': content_type,
            'file_size': len(file_data),
            'url': signed_url,
            'thumbnail_url': thumbnail_url,
            'path': file_path
        }
        
        return file_path, metadata
    
    def _get_signed_url(self, file_path: str, expires_in: int = 3600) -> str:
        """Generate a signed URL for temporary file access."""
        return self.client.storage.from_(self.bucket_name).create_signed_url(
            file_path,
            expires_in
        )
    
    def _generate_thumbnail_url(self, file_path: str) -> Optional[str]:
        """Generate a thumbnail URL for images and videos.
        This is a placeholder - implement actual thumbnail generation
        based on your requirements."""
        # For now, return the same signed URL
        # TODO: Implement actual thumbnail generation
        return self._get_signed_url(file_path)
    
    def delete_file(self, file_path: str) -> bool:
        """Delete a file from Supabase Storage."""
        try:
            self.client.storage.from_(self.bucket_name).remove([file_path])
            return True
        except Exception as e:
            print(f"Error deleting file {file_path}: {str(e)}")
            return False
    
    def get_file_metadata(self, file_path: str) -> Optional[Dict]:
        """Get metadata for a file."""
        try:
            # Get file info from Supabase
            file_info = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            return {
                'url': file_info,
                'path': file_path
            }
        except Exception as e:
            print(f"Error getting file metadata for {file_path}: {str(e)}")
            return None
    
    def update_file_metadata(
        self,
        file_path: str,
        metadata: Dict
    ) -> bool:
        """Update metadata for a file.
        Note: This is a placeholder as Supabase Storage doesn't support
        custom metadata directly. You might want to store metadata in
        your database instead."""
        # TODO: Implement if needed
        return True 
    
    def generate_upload_policy(
        self,
        file_name: str,
        instructor_id: int,
        asset_type: str,
        content_type: Optional[str] = None,
        max_size_bytes: Optional[int] = None
    ) -> Dict:
        """Generate an upload policy for direct-to-Supabase uploads.
        
        Args:
            file_name: Original file name
            instructor_id: ID of the instructor uploading the file
            asset_type: Type of asset (image, video, audio, animation)
            content_type: Optional content type override
            max_size_bytes: Optional maximum file size in bytes
            
        Returns:
            Dictionary containing upload policy and metadata
        """
        # Generate a unique upload ID
        upload_id = str(uuid.uuid4())
        
        # Generate the final file path
        file_path = self._generate_file_path(file_name, instructor_id, asset_type)
        
        # Get content type
        content_type = content_type or self._get_content_type(file_name)
        
        # Generate upload policy
        policy = {
            'upload_id': upload_id,
            'file_path': file_path,
            'content_type': content_type,
            'max_size_bytes': max_size_bytes or settings.MAX_FILE_SIZES.get(asset_type),
            'expires_at': (datetime.now() + timedelta(hours=1)).isoformat(),
            'bucket': self.bucket_name,
            'asset_type': asset_type,
            'instructor_id': instructor_id
        }
        
        # Sign the policy with Supabase
        signed_policy = self.client.storage.from_(self.bucket_name).create_signed_upload_url(
            file_path,
            policy['expires_at']
        )
        
        # Add signed URL to policy
        policy['signed_url'] = signed_policy
        
        return policy
    
    def verify_upload(
        self,
        upload_id: str,
        file_path: str,
        instructor_id: int
    ) -> Tuple[bool, Optional[Dict]]:
        """Verify that a file was uploaded successfully and get its metadata.
        
        Args:
            upload_id: The upload ID from the policy
            file_path: The file path in storage
            instructor_id: ID of the instructor who uploaded the file
            
        Returns:
            Tuple of (success, metadata)
        """
        try:
            # Verify file exists and belongs to instructor
            if not file_path.startswith(f"{instructor_id}/"):
                return False, None
            
            # Get file metadata
            file_info = self.client.storage.from_(self.bucket_name).get_public_url(file_path)
            
            # Generate signed URL
            signed_url = self._get_signed_url(file_path)
            
            # Generate thumbnail if needed
            thumbnail_url = None
            if file_path.split('/')[1] in ['image', 'video']:
                thumbnail_url = self._generate_thumbnail_url(file_path)
            
            metadata = {
                'file_path': file_path,
                'url': signed_url,
                'thumbnail_url': thumbnail_url,
                'upload_id': upload_id,
                'verified_at': datetime.now().isoformat()
            }
            
            return True, metadata
            
        except Exception as e:
            print(f"Error verifying upload {upload_id}: {str(e)}")
            return False, None
    
    def list_uploads(
        self,
        instructor_id: int,
        asset_type: Optional[str] = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict]:
        """List uploaded files for an instructor.
        
        Args:
            instructor_id: ID of the instructor
            asset_type: Optional filter by asset type
            limit: Maximum number of results
            offset: Pagination offset
            
        Returns:
            List of file metadata dictionaries
        """
        try:
            # Build path prefix
            prefix = f"{instructor_id}/"
            if asset_type:
                prefix = f"{prefix}{asset_type}/"
            
            # List files
            files = self.client.storage.from_(self.bucket_name).list(
                prefix,
                limit=limit,
                offset=offset
            )
            
            # Get metadata for each file
            results = []
            for file_info in files:
                file_path = f"{prefix}{file_info['name']}"
                signed_url = self._get_signed_url(file_path)
                
                metadata = {
                    'file_path': file_path,
                    'name': file_info['name'],
                    'size': file_info['metadata'].get('size', 0),
                    'created_at': file_info['metadata'].get('created_at'),
                    'url': signed_url
                }
                
                # Add thumbnail URL for images and videos
                if file_path.split('/')[1] in ['image', 'video']:
                    metadata['thumbnail_url'] = self._generate_thumbnail_url(file_path)
                
                results.append(metadata)
            
            return results
            
        except Exception as e:
            print(f"Error listing uploads for instructor {instructor_id}: {str(e)}")
            return []
    
    def delete_uploads(
        self,
        file_paths: List[str],
        instructor_id: int
    ) -> Dict[str, List[str]]:
        """Delete multiple files from storage.
        
        Args:
            file_paths: List of file paths to delete
            instructor_id: ID of the instructor who owns the files
            
        Returns:
            Dictionary with lists of successful and failed deletions
        """
        results = {
            'successful': [],
            'failed': []
        }
        
        for file_path in file_paths:
            try:
                # Verify file belongs to instructor
                if not file_path.startswith(f"{instructor_id}/"):
                    results['failed'].append(file_path)
                    continue
                
                # Delete file
                if self.delete_file(file_path):
                    results['successful'].append(file_path)
                else:
                    results['failed'].append(file_path)
                    
            except Exception as e:
                print(f"Error deleting file {file_path}: {str(e)}")
                results['failed'].append(file_path)
        
        return results 