"""
S3Handler - S3 operations for videos, frames, and results.

This module handles all S3 operations including downloading videos,
uploading frames, and managing golden standards and evaluation results.
"""

import json
import os
import cv2
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime


class S3Handler:
    """
    Handles S3 operations for the Yoga Evaluation System.
    
    Manages video downloads, frame uploads, and JSON data storage.
    """
    
    def __init__(self, s3_client, bucket_name: str):
        """
        Initialize S3Handler.
        
        Args:
            s3_client: boto3 S3 client
            bucket_name: Name of the S3 bucket
        """
        self.s3_client = s3_client
        self.bucket_name = bucket_name
    
    def download_video(self, key: str, local_path: str) -> None:
        """
        Download video from S3 to local path.
        
        Args:
            key: S3 object key
            local_path: Local file path to save video
        
        Raises:
            Exception: If download fails
        """
        # Ensure directory exists
        os.makedirs(os.path.dirname(local_path), exist_ok=True)
        
        # Download file
        self.s3_client.download_file(self.bucket_name, key, local_path)
    
    def upload_frames(
        self,
        frames: List[np.ndarray],
        s3_prefix: str,
        frame_format: str = 'jpg'
    ) -> List[str]:
        """
        Upload frames to S3 and return S3 keys.
        
        Args:
            frames: List of frames as numpy arrays
            s3_prefix: S3 prefix (folder path) for frames
            frame_format: Image format (default: 'jpg')
        
        Returns:
            List of S3 keys for uploaded frames
        """
        uploaded_keys = []
        
        for idx, frame in enumerate(frames):
            # Encode frame
            _, buffer = cv2.imencode(f'.{frame_format}', frame)
            frame_bytes = buffer.tobytes()
            
            # Generate S3 key
            key = f"{s3_prefix}/frame_{idx:04d}.{frame_format}"
            
            # Upload to S3
            self.s3_client.put_object(
                Bucket=self.bucket_name,
                Key=key,
                Body=frame_bytes,
                ContentType=f'image/{frame_format}'
            )
            
            uploaded_keys.append(key)
        
        return uploaded_keys
    
    def save_golden_standard(self, data: Dict, pose_name: str) -> str:
        """
        Save golden standard JSON to S3.
        
        Args:
            data: Golden standard dictionary
            pose_name: Name of the yoga pose
        
        Returns:
            S3 key of saved golden standard
        """
        key = f"{pose_name}/training/golden-standard.json"
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        
        return key
    
    def load_golden_standard(self, pose_name: str) -> Dict:
        """
        Load golden standard JSON from S3.
        
        Args:
            pose_name: Name of the yoga pose
        
        Returns:
            Golden standard dictionary
        
        Raises:
            Exception: If golden standard not found or invalid
        """
        key = f"{pose_name}/training/golden-standard.json"
        
        try:
            response = self.s3_client.get_object(
                Bucket=self.bucket_name,
                Key=key
            )
            data = json.loads(response['Body'].read().decode('utf-8'))
            return data
        except self.s3_client.exceptions.NoSuchKey:
            raise FileNotFoundError(
                f"Golden standard not found for pose: {pose_name}. "
                f"Please upload and process a training video first."
            )
    
    def save_evaluation(
        self,
        data: Dict,
        pose_name: str,
        video_name: str
    ) -> str:
        """
        Save evaluation JSON to S3.
        
        Args:
            data: Evaluation result dictionary
            pose_name: Name of the yoga pose
            video_name: Name of the test video (without extension)
        
        Returns:
            S3 key of saved evaluation
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        key = f"{pose_name}/testing/evaluations/{video_name}_{timestamp}_evaluation.json"
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(data, indent=2),
            ContentType='application/json'
        )
        
        return key
    
    def save_error_report(
        self,
        error_data: Dict,
        pose_name: str,
        video_name: str,
        stage: str
    ) -> str:
        """
        Save error report to S3.
        
        Args:
            error_data: Error information dictionary
            pose_name: Name of the yoga pose
            video_name: Name of the video
            stage: Processing stage where error occurred
        
        Returns:
            S3 key of saved error report
        """
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        key = f"{pose_name}/errors/{video_name}_{stage}_{timestamp}_error.json"
        
        self.s3_client.put_object(
            Bucket=self.bucket_name,
            Key=key,
            Body=json.dumps(error_data, indent=2),
            ContentType='application/json'
        )
        
        return key
