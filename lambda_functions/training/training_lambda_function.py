"""
Training Lambda Function - Process training videos and create golden standards.

This Lambda function processes training videos uploaded to S3, extracts frames,
analyzes yoga poses, and creates golden standard angle data for evaluation.
"""

import json
import os
import boto3
from typing import Dict, Any
from shared import YogaPoseAnalyzer, VideoProcessor, S3Handler


# Initialize AWS clients
s3_client = boto3.client('s3')
bedrock_client = boto3.client('bedrock-runtime')

# Environment variables
BUCKET_NAME = os.environ.get('BUCKET_NAME', 'yoga-evaluation-bucket')

# Pose display names
POSES = {
    "downward-dog": "Downward Facing Dog",
    "warrior-1": "Warrior I",
    "warrior-2": "Warrior II",
    "tree-pose": "Tree Pose",
    "triangle-pose": "Triangle Pose"
}


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for training video processing.
    
    Expected S3 event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "pose-name/training/video.mp4"}
            }
        }]
    }
    
    Args:
        event: S3 event trigger
        context: Lambda context
    
    Returns:
        Response dictionary with status and results
    """
    import time
    start_time = time.time()
    
    print(f"Received event: {json.dumps(event)}")
    
    # Initialize handlers
    s3_handler = S3Handler(s3_client, BUCKET_NAME)
    video_processor = VideoProcessor(bedrock_client)
    
    temp_files = []
    
    try:
        # Parse S3 event
        record = event['Records'][0]
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(f"Processing training video: s3://{bucket}/{key}")
        
        # Extract pose name from key (format: pose-name/training/video.mp4)
        key_parts = key.split('/')
        if len(key_parts) < 3 or key_parts[1] != 'training':
            raise ValueError(
                f"Invalid S3 key format. Expected: pose-name/training/video.mp4, got: {key}"
            )
        
        pose_name = key_parts[0]
        video_filename = os.path.basename(key)
        
        print(f"Pose: {pose_name}, Video: {video_filename}")
        
        # Download video to /tmp
        local_video_path = f"/tmp/{video_filename}"
        temp_files.append(local_video_path)
        
        print(f"Downloading video from S3...")
        download_start = time.time()
        s3_handler.download_video(key, local_video_path)
        download_duration = time.time() - download_start
        print(f"⏱️  [TIMING] Download: {download_duration:.2f}s")
        
        # Validate video contains correct pose using Bedrock (3 frames - OPTIMIZED)
        print(f"Validating video with Bedrock (analyzing 5 frames)...")
        validation_start = time.time()
        validation_result = video_processor.validate_video_with_bedrock(
            local_video_path,
            pose_name,
            sample_frames=5,
            s3_handler=s3_handler,
            video_filename=video_filename
        )
        validation_duration = time.time() - validation_start
        print(f"⏱️  [TIMING] Validation: {validation_duration:.2f}s")
        
        print(f"Validation result: {validation_result['message']}")
        print(f"Frames analyzed: {validation_result.get('frames_analyzed', 0)}")
        print(f"Frames valid: {validation_result.get('frames_valid', 0)}")
        if validation_result.get('validation_frames_s3'):
            print(f"Validation frames saved to S3: {len(validation_result['validation_frames_s3'])} frames")
        
        if not validation_result['is_valid']:
            error_data = {
                'error': 'Video validation failed',
                'pose_name': pose_name,
                'video_source': video_filename,
                'validation_result': validation_result,
                'stage': 'validation'
            }
            error_key = s3_handler.save_error_report(
                error_data,
                pose_name,
                video_filename.replace('.mp4', ''),
                'validation'
            )
            
            # Get detected pose from validation
            detected_pose = validation_result.get('detected_pose', 'unknown')
            frames_valid = validation_result.get('frames_valid', 0)
            frames_analyzed = validation_result.get('frames_analyzed', 0)
            
            # Create user-friendly message
            if detected_pose and detected_pose != 'unknown' and detected_pose != pose_name:
                user_message = f"We detected {detected_pose.replace('-', ' ').title()} in your video, but you selected {POSES.get(pose_name, pose_name)}."
                recommendation = f"Please upload a video showing {POSES.get(pose_name, pose_name)}, or select the correct pose type that matches your video."
            else:
                user_message = f"We couldn't clearly identify {POSES.get(pose_name, pose_name)} in your video."
                recommendation = "Please ensure:\n• The person is fully visible in the frame\n• The pose is held clearly for most of the video\n• Good lighting and camera angle\n• Minimal background distractions"
            
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': f'Video Validation Failed',
                    'user_message': user_message,
                    'pose_display_name': POSES.get(pose_name, pose_name),
                    'validation_summary': f"Only {frames_valid} out of {frames_analyzed} frames matched the expected pose",
                    'recommendation': recommendation
                })
            }
        
        # Extract frames from video
        print(f"Extracting frames from video...")
        extraction_start = time.time()
        frames = video_processor.extract_frames(
            local_video_path,
            fps=2,  # 2 frames per second
            max_frames=60  # Max 30 seconds of video
        )
        extraction_duration = time.time() - extraction_start
        print(f"⏱️  [TIMING] Extraction: {extraction_duration:.2f}s")
        
        print(f"Extracted {len(frames)} frames")
        
        if len(frames) < 10:
            raise ValueError(
                f"Insufficient frames extracted: {len(frames)}. "
                "Video should be at least 5 seconds long."
            )
        
        # Upload frames to S3
        print(f"Uploading frames to S3...")
        frame_prefix = f"{pose_name}/training/frames/{video_filename.replace('.mp4', '')}"
        frame_keys = s3_handler.upload_frames(frames, frame_prefix)
        
        print(f"Uploaded {len(frame_keys)} frames")
        
        # Initialize pose analyzer with optimized threshold
        print(f"Initializing pose analyzer for {pose_name}...")
        analyzer = YogaPoseAnalyzer(pose_name, visibility_threshold=0.3)
        print(f"Using visibility threshold: 0.3 (optimized for better detection)")
        
        # Process frames and extract angles
        print(f"Analyzing poses in frames...")
        analysis_start = time.time()
        angle_data = []
        
        for idx, frame in enumerate(frames):
            # Detect landmarks
            landmarks = analyzer.detect_pose_landmarks(frame)
            
            if landmarks:
                # Calculate angles
                angles = analyzer.calculate_angles(landmarks)
                
                if angles:
                    angle_data.append(angles)
                    print(f"Frame {idx}: Detected {len(angles)} angles")
        
        analysis_duration = time.time() - analysis_start
        print(f"⏱️  [TIMING] Analysis: {analysis_duration:.2f}s")
        
        # Calculate pose detection rate
        pose_detection_rate = len(angle_data) / len(frames) if len(frames) > 0 else 0.0
        print(f"📊 [POSE DETECTION] Successfully analyzed {len(angle_data)}/{len(frames)} frames ({pose_detection_rate*100:.1f}%)")
        
        # Validate minimum pose detection rate (50%)
        if pose_detection_rate < 0.5:
            error_msg = (
                f"Insufficient pose detection rate: {pose_detection_rate*100:.1f}% "
                f"({len(angle_data)}/{len(frames)} frames). "
                "Minimum required: 50%. "
                "Recommendations: Ensure person is fully visible, improve lighting, "
                "avoid loose clothing, use plain background."
            )
            print(f"❌ [POSE DETECTION] {error_msg}")
            raise ValueError(error_msg)
        
        # Warn if below target (80%)
        if pose_detection_rate < 0.8:
            print(f"⚠️  [POSE DETECTION] Detection rate below target (80%). Consider improving video quality.")
        
        if len(angle_data) < 5:
            raise ValueError(
                f"Insufficient pose data extracted: {len(angle_data)} frames. "
                "Ensure the person is clearly visible and performing the pose correctly."
            )
        
        # Create golden standard
        print(f"Creating golden standard...")
        golden_standard = analyzer.create_golden_standard(
            angle_data,
            video_filename,
            metadata={
                'total_frames_extracted': len(frames),
                'frames_with_pose_data': len(angle_data),
                'validation_result': validation_result,
                'frame_keys': frame_keys[:5]  # Store first 5 frame keys as sample
            }
        )
        
        # Save golden standard to S3
        print(f"Saving golden standard to S3...")
        golden_standard_key = s3_handler.save_golden_standard(
            golden_standard,
            pose_name
        )
        
        print(f"Golden standard saved: {golden_standard_key}")
        
        # Calculate total processing time
        total_duration = time.time() - start_time
        print(f"⏱️  [TIMING] Total processing time: {total_duration:.2f}s")
        print(f"📊 [TIMING BREAKDOWN] Download: {download_duration:.2f}s | Validation: {validation_duration:.2f}s | Extraction: {extraction_duration:.2f}s | Analysis: {analysis_duration:.2f}s")
        
        # Cleanup
        video_processor.cleanup_temp_files(temp_files)
        
        # Return success response with user-friendly formatting
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Golden Standard Created Successfully!',
                'user_message': f'Your {POSES.get(pose_name, pose_name)} training video has been processed and is ready to use for evaluations.',
                'pose_display_name': POSES.get(pose_name, pose_name),
                'golden_standard_key': golden_standard_key,
                'summary': {
                    'video_duration': f"{len(frames)/2:.1f}s",
                    'frames_analyzed': len(angle_data),
                    'detection_rate': f"{pose_detection_rate*100:.0f}%",
                    'validation_confidence': f"{validation_result.get('confidence', 0)*100:.0f}%",
                    'processing_time': f"{total_duration:.1f}s"
                }
            })
        }
        
        print(f"Training complete: {response}")
        return response
        
    except Exception as e:
        print(f"Error processing training video: {str(e)}")
        
        # Save error report
        try:
            error_data = {
                'error': str(e),
                'error_type': type(e).__name__,
                'event': event,
                'stage': 'processing'
            }
            
            # Try to extract pose name and video name for error report
            try:
                key = event['Records'][0]['s3']['object']['key']
                pose_name = key.split('/')[0]
                video_filename = os.path.basename(key)
                
                error_key = s3_handler.save_error_report(
                    error_data,
                    pose_name,
                    video_filename.replace('.mp4', ''),
                    'processing'
                )
                print(f"Error report saved: {error_key}")
            except:
                pass
        except:
            pass
        
        # Cleanup
        try:
            video_processor.cleanup_temp_files(temp_files)
        except:
            pass
        
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Error processing training video',
                'error': str(e)
            })
        }
