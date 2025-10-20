"""
Testing Lambda Function - Evaluate test videos against golden standards.

This Lambda function processes test videos uploaded to S3, extracts frames,
analyzes yoga poses, and evaluates them against golden standard angle data.
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


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda handler for test video evaluation.
    
    Expected S3 event structure:
    {
        "Records": [{
            "s3": {
                "bucket": {"name": "bucket-name"},
                "object": {"key": "pose-name/testing/video.mp4"}
            }
        }]
    }
    
    Args:
        event: S3 event trigger
        context: Lambda context
    
    Returns:
        Response dictionary with evaluation results
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
        
        print(f"Processing test video: s3://{bucket}/{key}")
        
        # Extract pose name from key (format: pose-name/testing/video.mp4)
        key_parts = key.split('/')
        if len(key_parts) < 3 or key_parts[1] != 'testing':
            raise ValueError(
                f"Invalid S3 key format. Expected: pose-name/testing/video.mp4, got: {key}"
            )
        
        pose_name = key_parts[0]
        video_filename = os.path.basename(key)
        
        print(f"Pose: {pose_name}, Video: {video_filename}")
        
        # Load golden standard
        print(f"Loading golden standard for {pose_name}...")
        try:
            golden_standard = s3_handler.load_golden_standard(pose_name)
            print(f"Golden standard loaded successfully")
        except FileNotFoundError as e:
            error_data = {
                'error': str(e),
                'pose_name': pose_name,
                'video_source': video_filename,
                'stage': 'golden_standard_loading'
            }
            error_key = s3_handler.save_error_report(
                error_data,
                pose_name,
                video_filename.replace('.mp4', ''),
                'golden_standard_loading'
            )
            
            return {
                'statusCode': 404,
                'body': json.dumps({
                    'message': str(e),
                    'error_report': error_key
                })
            }
        
        # Download video to /tmp
        local_video_path = f"/tmp/{video_filename}"
        temp_files.append(local_video_path)
        
        print(f"Downloading video from S3...")
        download_start = time.time()
        s3_handler.download_video(key, local_video_path)
        download_duration = time.time() - download_start
        print(f"⏱️  [TIMING] Download: {download_duration:.2f}s")
        
        # Validate video contains correct pose using Bedrock (3 frames - OPTIMIZED)
        # FIXED: Removed duplicate validation that was adding ~35 seconds
        print(f"Validating video with Bedrock (analyzing 3 frames)...")
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
            # Extract Claude's reasoning from frame results for user feedback
            frame_analyses = []
            for frame_result in validation_result.get('frame_results', []):
                if frame_result.get('analysis'):
                    frame_analyses.append(frame_result['analysis'])
            
            # Create user-friendly feedback
            pose_display_name = pose_name.replace('-', ' ').title()
            frames_valid = validation_result.get('frames_valid', 0)
            frames_total = validation_result.get('frames_analyzed', 0)
            
            user_message = f"The video does not show {pose_display_name} clearly enough"
            validation_summary = f"Only {frames_valid} out of {frames_total} frames were recognized as {pose_display_name}"
            
            # Build recommendation based on Claude's feedback
            recommendation = f"Please upload a video showing {pose_display_name}:\n"
            recommendation += "• Ensure you're performing the correct pose\n"
            recommendation += "• Hold the pose steady for at least 3-5 seconds\n"
            recommendation += "• Make sure your full body is visible in the frame\n"
            recommendation += "• Use good lighting and a plain background\n"
            recommendation += f"• Check the validation frames in S3 to see what was detected"
            
            error_data = {
                'error': 'Video validation failed',
                'pose_name': pose_name,
                'video_source': video_filename,
                'validation_result': validation_result,
                'stage': 'validation',
                'user_message': user_message,
                'validation_summary': validation_summary,
                'recommendation': recommendation,
                'claude_analyses': frame_analyses
            }
            error_key = s3_handler.save_error_report(
                error_data,
                pose_name,
                video_filename.replace('.mp4', ''),
                'validation'
            )
            
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'status': 'error',
                    'pose_name': pose_name,
                    'pose_display_name': pose_display_name,
                    'user_message': user_message,
                    'validation_summary': validation_summary,
                    'recommendation': recommendation,
                    'frames_analyzed': frames_total,
                    'frames_valid': frames_valid,
                    'validation_frames_s3': validation_result.get('validation_frames_s3', []),
                    'claude_feedback': frame_analyses[:2] if len(frame_analyses) > 0 else [],  # Show first 2 analyses
                    'error_report': error_key,
                    'message': 'Video validation failed'
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
        
        if len(frames) < 5:
            raise ValueError(
                f"Insufficient frames extracted: {len(frames)}. "
                "Video should be at least 3 seconds long."
            )
        
        # Upload frames to S3 (ALIGNED WITH TRAINING PROCESS)
        # This ensures consistency and enables debugging
        print(f"Uploading frames to S3...")
        frame_prefix = f"{pose_name}/testing/frames/{video_filename.replace('.mp4', '')}"
        frame_keys = s3_handler.upload_frames(frames, frame_prefix)
        print(f"Uploaded {len(frame_keys)} frames to S3")
        
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
        
        if len(angle_data) < 3:
            raise ValueError(
                f"Insufficient pose data extracted: {len(angle_data)} frames. "
                "Ensure the person is clearly visible and performing the pose correctly."
            )
        
        # Evaluate against golden standard
        print(f"Evaluating against golden standard...")
        evaluation = analyzer.evaluate_angles(angle_data, golden_standard)
        
        # Generate feedback
        print(f"Generating feedback...")
        result = analyzer.generate_feedback(
            evaluation,
            video_filename,
            pass_threshold=70.0
        )
        
        # Add validation result and pose detection metrics to final output
        result['validation_result'] = validation_result
        result['frames_with_pose'] = len(angle_data)
        result['total_frames'] = len(frames)
        result['pose_detection_rate'] = pose_detection_rate
        
        # Build user-friendly feedback summary
        pose_display_name = pose_name.replace('-', ' ').title()
        overall_score = result['overall_score']
        grade = result['grade']
        pass_fail = result['pass_fail']
        
        # Categorize angles by performance
        excellent_angles = []
        good_angles = []
        needs_improvement = []
        
        for angle_name, angle_eval in result.get('angle_evaluations', {}).items():
            angle_display = angle_name.replace('_', ' ').title()
            score = angle_eval.get('score', 0)
            
            if score >= 85:
                excellent_angles.append(angle_display)
            elif score >= 70:
                good_angles.append(angle_display)
            else:
                needs_improvement.append(angle_display)
        
        # Build "What You Did Right" section
        what_you_did_right = []
        if excellent_angles:
            what_you_did_right.append(f"✓ Excellent alignment: {', '.join(excellent_angles)}")
        if good_angles:
            what_you_did_right.append(f"✓ Good form: {', '.join(good_angles)}")
        if pass_fail == "PASS":
            what_you_did_right.append(f"✓ Overall score of {overall_score:.1f} meets the passing threshold")
        if pose_detection_rate >= 0.8:
            what_you_did_right.append(f"✓ Excellent pose consistency ({pose_detection_rate*100:.0f}% detection rate)")
        
        # Build "What Can Be Improved" section
        what_can_improve = []
        if needs_improvement:
            what_can_improve.append(f"• Focus on: {', '.join(needs_improvement)}")
        if pose_detection_rate < 0.8:
            what_can_improve.append(f"• Improve pose stability (current: {pose_detection_rate*100:.0f}%, target: 80%+)")
        if overall_score < 90:
            what_can_improve.append(f"• Work on overall alignment to reach excellent range (90+)")
        
        # Add specific recommendations from angle evaluations
        for angle_name, angle_eval in result.get('angle_evaluations', {}).items():
            if angle_eval.get('score', 0) < 70 and angle_eval.get('feedback'):
                what_can_improve.append(f"• {angle_eval['feedback']}")
        
        # Create comprehensive user feedback
        user_feedback = {
            'overall_assessment': result.get('summary_feedback', ''),
            'what_you_did_right': what_you_did_right if what_you_did_right else ['Keep practicing!'],
            'what_can_improve': what_can_improve if what_can_improve else ['Great job! Keep maintaining this form.'],
            'key_metrics': {
                'score': f"{overall_score:.1f}/100",
                'grade': grade,
                'result': pass_fail,
                'pose_consistency': f"{pose_detection_rate*100:.0f}%",
                'frames_analyzed': f"{len(angle_data)}/{len(frames)}"
            }
        }
        
        # Add to result
        result['user_feedback'] = user_feedback
        result['pose_display_name'] = pose_display_name
        
        # Save evaluation to S3
        print(f"Saving evaluation to S3...")
        evaluation_key = s3_handler.save_evaluation(
            result,
            pose_name,
            video_filename.replace('.mp4', '')
        )
        
        print(f"Evaluation saved: {evaluation_key}")
        
        # Calculate total processing time
        total_duration = time.time() - start_time
        print(f"⏱️  [TIMING] Total processing time: {total_duration:.2f}s")
        print(f"📊 [TIMING BREAKDOWN] Download: {download_duration:.2f}s | Validation: {validation_duration:.2f}s | Extraction: {extraction_duration:.2f}s | Analysis: {analysis_duration:.2f}s")
        
        # Cleanup
        video_processor.cleanup_temp_files(temp_files)
        
        # Return success response with enhanced feedback (flatten result to top level)
        response = {
            'statusCode': 200,
            'body': json.dumps({
                'status': 'success',
                'message': 'Test video evaluated successfully',
                'evaluation_key': evaluation_key,
                **result  # Spread result fields to top level for UI
            })
        }
        
        print(f"Evaluation complete: Overall score = {result['overall_score']:.2f}, Grade = {result['grade']}, Pass/Fail = {result['pass_fail']}")
        return response
        
    except Exception as e:
        print(f"Error processing test video: {str(e)}")
        
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
                'message': 'Error processing test video',
                'error': str(e)
            })
        }
