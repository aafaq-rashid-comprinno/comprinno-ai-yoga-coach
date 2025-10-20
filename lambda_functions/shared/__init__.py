"""
Shared components for Yoga Evaluation System.

This package contains shared modules used by both training and testing Lambda functions:
- YogaPoseAnalyzer: Core pose analysis and evaluation logic
- VideoProcessor: Video validation and frame extraction
- S3Handler: S3 operations for videos, frames, and results
"""

from .yoga_pose_analyzer import YogaPoseAnalyzer
from .video_processor import VideoProcessor
from .s3_handler import S3Handler

__version__ = "1.0.0"
__all__ = [
    'YogaPoseAnalyzer',
    'VideoProcessor',
    'S3Handler'
]
