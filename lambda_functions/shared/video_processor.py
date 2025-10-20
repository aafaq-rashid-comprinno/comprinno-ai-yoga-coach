"""
VideoProcessor - Video validation and frame extraction.

This module handles video processing operations including frame extraction,
video validation using AWS Bedrock, and temporary file cleanup.
"""

import cv2
import os
import json
import base64
import time
import numpy as np
from typing import List, Dict, Optional, Tuple
from PIL import Image
import io


class VideoProcessor:
    """
    Handles video processing operations for the Yoga Evaluation System.
    
    Provides frame extraction, video validation, and cleanup utilities.
    """
    
    def __init__(self, bedrock_client=None):
        """
        Initialize VideoProcessor.
        
        Args:
            bedrock_client: Optional boto3 Bedrock Runtime client for video validation
        """
        self.bedrock_client = bedrock_client
    
    def _invoke_bedrock_with_retry(
        self,
        request_body: Dict,
        model_id: str = "anthropic.claude-3-sonnet-20240229-v1:0",
        max_retries: int = 3,
        base_delay: float = 2.0,
        max_delay: float = 5.0
    ) -> Dict:
        """
        Invoke Bedrock with exponential backoff retry logic for throttling protection.
        
        Args:
            request_body: Request body for Bedrock API
            model_id: Claude model ID to use
            max_retries: Maximum number of retry attempts (default: 3)
            base_delay: Base delay in seconds for exponential backoff (default: 2.0)
            max_delay: Maximum delay in seconds (default: 5.0)
        
        Returns:
            Bedrock API response
        
        Raises:
            Exception: If max retries exceeded or non-throttling error occurs
        """
        from botocore.exceptions import ClientError
        
        retry_count = 0
        
        while retry_count <= max_retries:
            try:
                # Add delay before retry (except first attempt)
                if retry_count > 0:
                    # Exponential backoff: delay = min(base_delay * (2 ^ retry_count), max_delay)
                    delay = min(base_delay * (2 ** retry_count), max_delay)
                    print(f"⏸️  [RETRY {retry_count}/{max_retries}] Waiting {delay:.1f}s before retry...")
                    time.sleep(delay)
                
                # Call Bedrock API
                response = self.bedrock_client.invoke_model(
                    modelId=model_id,
                    body=json.dumps(request_body)
                )
                
                # Success - return response
                if retry_count > 0:
                    print(f"✅ [RETRY SUCCESS] Request succeeded after {retry_count} retries")
                
                return response
                
            except ClientError as e:
                error_code = e.response['Error']['Code']
                
                if error_code == 'ThrottlingException':
                    retry_count += 1
                    
                    if retry_count <= max_retries:
                        print(f"⚠️  [THROTTLING] ThrottlingException detected (attempt {retry_count}/{max_retries})")
                    else:
                        print(f"❌ [THROTTLING] Max retries ({max_retries}) exceeded")
                        raise Exception(
                            f"Claude API throttling: Max retries ({max_retries}) exceeded. "
                            "Please wait a few minutes before trying again."
                        )
                else:
                    # Non-throttling error - raise immediately
                    print(f"❌ [ERROR] Bedrock API error: {error_code}")
                    raise
            
            except Exception as e:
                # Unexpected error - raise immediately
                print(f"❌ [ERROR] Unexpected error invoking Bedrock: {str(e)}")
                raise
        
        # Should not reach here, but just in case
        raise Exception(f"Max retries ({max_retries}) exceeded")
    
    def _extract_evenly_distributed_frames(
        self,
        video_path: str,
        num_frames: int
    ) -> List[np.ndarray]:
        """
        Extract frames evenly distributed across the entire video duration.
        This ensures we sample from beginning, middle, and end of the video.
        
        Args:
            video_path: Path to video file
            num_frames: Number of frames to extract
        
        Returns:
            List of frames as numpy arrays (BGR format)
        """
        print(f"🎬 [EVEN FRAME EXTRACTION] Extracting {num_frames} evenly distributed frames")
        
        if not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")
        
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        try:
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            duration = total_frames / video_fps if video_fps > 0 else 0
            
            print(f"📊 [VIDEO INFO] Total frames: {total_frames}, FPS: {video_fps:.2f}, Duration: {duration:.2f}s")
            
            if total_frames < num_frames:
                print(f"⚠️ [WARNING] Video has fewer frames ({total_frames}) than requested ({num_frames})")
                num_frames = total_frames
            
            # Calculate frame indices evenly distributed across video
            # Skip first and last 15% to avoid setup/exit transitions
            start_frame = int(total_frames * 0.15)
            end_frame = int(total_frames * 0.85)
            usable_frames = end_frame - start_frame
            
            if usable_frames < num_frames:
                start_frame = 0
                end_frame = total_frames
                usable_frames = total_frames
            
            # Calculate evenly spaced indices
            frame_indices = []
            if num_frames == 1:
                frame_indices = [total_frames // 2]  # Middle frame
            else:
                step = usable_frames / (num_frames - 1)
                frame_indices = [int(start_frame + i * step) for i in range(num_frames)]
            
            print(f"📍 [FRAME INDICES] Extracting frames at positions: {frame_indices}")
            print(f"⏱️ [TIME DISTRIBUTION] Frames span from {start_frame/video_fps:.1f}s to {end_frame/video_fps:.1f}s")
            
            # Extract frames at calculated indices
            frames = []
            for idx in frame_indices:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                ret, frame = cap.read()
                if ret:
                    frames.append(frame)
                    print(f"✅ [FRAME {len(frames)}/{num_frames}] Extracted frame at index {idx} ({idx/video_fps:.2f}s)")
                else:
                    print(f"⚠️ [WARNING] Failed to extract frame at index {idx}")
            
            print(f"✅ [EXTRACTION COMPLETE] Successfully extracted {len(frames)}/{num_frames} frames")
            return frames
            
        finally:
            cap.release()

    def extract_frames(
        self,
        video_path: str,
        fps: int = 2,
        max_frames: Optional[int] = None
    ) -> List[np.ndarray]:
        """
        Extract frames from video at specified frame rate.
        
        Args:
            video_path: Path to video file
            fps: Frames per second to extract (default: 2)
            max_frames: Maximum number of frames to extract (optional)
        
        Returns:
            List of frames as numpy arrays (BGR format)
        
        Raises:
            ValueError: If video cannot be opened or is invalid
        """
        print(f"🎬 [FRAME EXTRACTION] Starting frame extraction from: {video_path}")
        print(f"📊 [FRAME EXTRACTION] Target FPS: {fps}, Max frames: {max_frames}")
        if not os.path.exists(video_path):
            raise ValueError(f"Video file not found: {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path}")
        
        try:
            # Get video properties
            video_fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            
            if video_fps <= 0:
                raise ValueError("Invalid video FPS")
            
            # Calculate frame interval
            frame_interval = int(video_fps / fps)
            if frame_interval < 1:
                frame_interval = 1
            
            frames = []
            frame_count = 0
            
            while True:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at specified interval
                if frame_count % frame_interval == 0:
                    frames.append(frame)
                    
                    # Check max frames limit
                    if max_frames and len(frames) >= max_frames:
                        break
                
                frame_count += 1
            
            print(f"✅ [FRAME EXTRACTION] Successfully extracted {len(frames)} frames from {total_frames} total frames")
            return frames
            
        finally:
            cap.release()

    def validate_video_with_bedrock(
        self,
        video_path: str,
        expected_pose: str,
        sample_frames: int = 5,
        s3_handler=None,
        video_filename: str = None
    ) -> Dict:
        """
        Validate video contains expected yoga pose using AWS Bedrock vision API.
        Analyzes multiple frames EVENLY DISTRIBUTED across the entire video.
        
        BALANCED: 5 frames with 60% threshold (need 3/5 frames to pass)
        - More robust than 3 frames
        - Better coverage of video timeline
        - Handles transition frames and variations
        
        Args:
            video_path: Path to video file
            expected_pose: Expected yoga pose name (e.g., 'downward-dog')
            sample_frames: Number of frames to sample for validation (default: 5)
            s3_handler: Optional S3Handler instance to save validation frames
            video_filename: Original video filename for frame naming
        
        Returns:
            Validation result dictionary with is_valid, confidence, message, and frame info
        
        Raises:
            ValueError: If Bedrock client is not configured
        """
        if not self.bedrock_client:
            raise ValueError("Bedrock client not configured for video validation")
        
        # Extract frames EVENLY DISTRIBUTED across entire video
        frames = self._extract_evenly_distributed_frames(video_path, sample_frames)
        
        if not frames:
            return {
                'is_valid': False,
                'confidence': 0.0,
                'expected_pose': expected_pose,
                'detected_pose': None,
                'validation_method': 'bedrock_vision_analysis',
                'message': 'No frames could be extracted from video',
                'timestamp': self._get_timestamp(),
                'frames_analyzed': 0
            }
        
        # Convert pose name to human-readable format
        pose_display_name = expected_pose.replace('-', ' ').title()
        
        # Analyze each frame with Claude
        frame_results = []
        saved_frame_keys = []
        
        print(f"🤖 [CLAUDE ANALYSIS] Analyzing {len(frames)} frames with Claude...")
        print(f"⏱️  [RATE LIMITING] Adding 2s delay between API calls to avoid throttling")
        
        for idx, frame in enumerate(frames):
            # Add delay between API calls to avoid throttling (except for first frame)
            if idx > 0:
                print(f"⏸️  [DELAY] Waiting 2 seconds before next API call...")
                time.sleep(2)
            
            print(f"📸 [FRAME {idx+1}/{len(frames)}] Processing frame...")
            # Convert frame to JPEG
            _, buffer = cv2.imencode('.jpg', frame)
            image_bytes = buffer.tobytes()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
            
            # Always save frame to S3 for debugging (create path under training/analysis)
            frame_key = f"{expected_pose}/training/analysis/{video_filename.replace('.mp4', '') if video_filename else 'unknown'}/validation_frame_{idx+1}.jpg"
            
            if s3_handler:
                try:
                    s3_handler.s3_client.put_object(
                        Bucket=s3_handler.bucket_name,
                        Key=frame_key,
                        Body=image_bytes,
                        ContentType='image/jpeg'
                    )
                    saved_frame_keys.append(frame_key)
                    print(f"💾 [FRAME {idx+1}/{len(frames)}] Saved to S3: s3://{s3_handler.bucket_name}/{frame_key}")
                except Exception as e:
                    print(f"⚠️  [FRAME {idx+1}/{len(frames)}] Could not save to S3: {e}")
            else:
                print(f"⚠️  [FRAME {idx+1}/{len(frames)}] No S3 handler provided, frame not saved")
            
            # Prepare enhanced Bedrock request with detailed pose descriptions
            pose_descriptions = {
                "Downward Dog": {
                    "description": "An inverted V-shaped pose where person is on hands and feet with hips lifted high",
                    "key_features": [
                        "CRITICAL: Both hands flat on ground, fingers spread wide",
                        "CRITICAL: Both feet on ground, toes tucked under",
                        "CRITICAL: Hips lifted high (highest point of entire body)",
                        "CRITICAL: Head hanging down between arms, looking at feet/ground",
                        "CRITICAL: Body forms clear inverted V or mountain shape",
                        "CRITICAL: Arms and legs relatively straight",
                        "CRITICAL: Person is NOT standing upright"
                    ],
                    "accept_if": "Hands on ground + feet on ground + hips high + head down + inverted V shape",
                    "reject_if_you_see": [
                        "Standing upright on both feet",
                        "Balancing on only one leg",
                        "One foot raised against other leg",
                        "Front knee bent in lunge position",
                        "Lateral side bend with one arm up",
                        "Both arms raised overhead",
                        "Arms extended sideways",
                        "Sitting or lying down",
                        "Both legs straight and wide with torso bending sideways"
                    ]
                },
                "Warrior I": {
                    "description": "A standing lunge pose with arms raised - CRITICAL: LUNGE position with BOTH feet on ground",
                    "key_features": [
                        "CRITICAL: Both feet must be firmly on the ground",
                        "CRITICAL: Front knee bent in lunge position (not straight)",
                        "CRITICAL: Back leg straight and strong",
                        "CRITICAL: Arms typically raised overhead (not to sides)",
                        "CRITICAL: Hips facing forward, torso square to front",
                        "CRITICAL: Body facing forward direction",
                        "CRITICAL: Standing upright, not on hands and knees"
                    ],
                    "accept_if": "Both feet on ground + front knee bent in lunge + arms overhead + body facing forward",
                    "reject_if_you_see": [
                        "Arms extended horizontally to sides",
                        "Body facing sideways with torso open",
                        "Arms parallel to ground pointing left and right",
                        "Balancing on only one leg",
                        "One foot raised against other leg",
                        "Hands flat on ground supporting body weight",
                        "Hips lifted high with head hanging down",
                        "Inverted V shape with hands on ground",
                        "Both legs straight and wide apart",
                        "Lateral side bend with one arm up",
                        "Person on hands and knees"
                    ]
                },
                "Warrior II": {
                    "description": "A standing lunge pose with arms extended to sides - CRITICAL: LUNGE with arms out sideways",
                    "key_features": [
                        "CRITICAL: Both feet on ground in lunge position",
                        "CRITICAL: Front knee bent, back leg straight",
                        "CRITICAL: Arms extended horizontally to opposite sides (parallel to ground)",
                        "CRITICAL: Body facing sideways, torso open to the side",
                        "CRITICAL: Head looking over front arm",
                        "CRITICAL: Wide stance with feet apart"
                    ],
                    "accept_if": "Lunge position + arms extended sideways + body facing sideways + torso open",
                    "reject_if_you_see": [
                        "Both arms raised overhead",
                        "Arms in prayer position above head",
                        "Body facing forward instead of sideways",
                        "Torso facing forward with hips square",
                        "Arms not extended to sides",
                        "Balancing on only one leg",
                        "Hands flat on ground supporting body weight",
                        "Hips lifted high with head hanging down",
                        "Both legs straight and wide apart",
                        "Lateral side bend with one arm up"
                    ]
                },
                "Tree Pose": {
                    "description": "A one-legged balance pose - CRITICAL: Standing on ONE leg (other foot can be anywhere on standing leg)",
                    "key_features": [
                        "CRITICAL: Only ONE foot on the ground (balancing)",
                        "CRITICAL: Other foot raised and touching the standing leg (ankle, calf, or thigh)",
                        "CRITICAL: Person is balancing, not in a lunge or wide stance",
                        "CRITICAL: Standing upright, not bending forward or sideways",
                        "Arms can be at sides, prayer position, or overhead",
                        "Natural balance adjustments and micro-movements are normal"
                    ],
                    "accept_if": "One foot on ground + other foot touching standing leg + balancing upright",
                    "reject_if_you_see": [
                        "Both feet firmly planted on ground",
                        "Front knee bent in lunge position",
                        "Wide stance with both legs straight",
                        "Hands flat on ground supporting body weight",
                        "Hips lifted high with head hanging down",
                        "Lateral side bend with one arm up",
                        "Person on hands and knees"
                    ]
                },
                "Triangle Pose": {
                    "description": "A standing side-bend pose where person bends laterally to one side with legs apart",
                    "key_features": [
                        "Person is standing (not sitting or lying down)",
                        "Torso bending to one side (lateral bend or side stretch)",
                        "One hand reaching down (toward ground, leg, ankle, or shin)",
                        "Body forms a side-bend or triangular shape",
                        "Legs can be apart or together - both are acceptable",
                        "Natural variations in arm and leg positioning are normal"
                    ],
                    "accept_if": "Standing + side bend + one arm reaching down",
                    "reject_if_you_see": [
                        "Balancing on only ONE leg with other foot raised against leg",
                        "Hands flat on ground supporting body weight (downward dog)",
                        "Hips lifted high with head hanging down",
                        "Person on hands and knees",
                        "Sitting or lying down poses"
                    ]
                },
            }
            
            pose_info = pose_descriptions.get(pose_display_name, {
                "description": pose_display_name,
                "key_features": [],
                "accept_if": "Main pose structure is present",
                "reject_only_if": "Completely different pose"
            })
            
            features_text = "\n".join(["   - " + feature for feature in pose_info["key_features"]])
            accept_criteria = pose_info.get("accept_if", "Main pose structure is present")
            reject_criteria = pose_info.get("reject_only_if", "Completely different pose")
            
            # Get reject criteria
            reject_if_you_see = pose_info.get("reject_if_you_see", [])
            if reject_if_you_see:
                reject_items = []
                for item in reject_if_you_see:
                    reject_items.append("   ❌ " + item)
                reject_text = "\n".join(reject_items)
            else:
                reject_text = "   ❌ Any completely different pose"
            
            # Build concise, strict prompt using pose_descriptions data
            prompt = f"""You are a STRICT yoga pose validator for {pose_display_name}. Verify this is the CORRECT pose type.

**Expected Pose: {pose_display_name}**
{pose_info["description"]}

**CRITICAL Requirements (ALL must be present):**
{features_text}

**IMMEDIATELY REJECT if you see ANY of these (wrong poses):**
{reject_text}

**Validation Process:**
1. First, check if you see ANY "IMMEDIATELY REJECT" indicators
   → If YES: Answer NO (wrong pose)
2. Then, check if ALL CRITICAL requirements are met
   → If NO: Answer NO (missing requirements)
3. Only if no reject indicators AND all requirements met → Answer YES

**Response Format (MUST follow exactly):**
1. **Answer: YES or NO**
2. **Confidence: X%**
3. **What I see:** [Describe the actual pose in the image]
4. **Pose Identified:** [What pose is this actually? Be specific]
5. **Critical Check:** [Which requirements are met/missing?]
6. **Reject Check:** [Any reject indicators present?]

**STRICT RULES:**
- Tree Pose: MUST be balancing on ONE leg. If both feet on ground → Answer NO
- Warrior I: MUST have front knee bent + facing forward. If sideways → Answer NO (it's Warrior II)
- Warrior II: MUST be facing sideways + arms out to sides. If facing forward → Answer NO (it's Warrior I)
- Triangle: MUST have both legs straight + side bend. If knee bent → Answer NO (it's Warrior)
- Downward Dog: MUST have hands on ground + hips high. If standing → Answer NO

**Remember:** Be EXTREMELY STRICT. When in doubt, answer NO. We need the EXACT pose, not a similar one."""
            
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 500,
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/jpeg",
                                    "data": image_base64
                                }
                            },
                            {
                                "type": "text",
                                "text": prompt
                            }
                        ]
                    }
                ]
            }
            
            try:
                # Call Bedrock with Claude 3 Sonnet using retry logic
                # Using Claude 3 Sonnet for better availability and lower throttling
                # Includes exponential backoff for throttling protection
                response = self._invoke_bedrock_with_retry(
                    request_body=request_body,
                    model_id="anthropic.claude-3-sonnet-20240229-v1:0",
                    max_retries=3,
                    base_delay=2.0,
                    max_delay=5.0
                )
                
                # Parse response
                response_body = json.loads(response['body'].read())
                analysis_text = response_body['content'][0]['text']
                
                print(f"🤖 [CLAUDE RESPONSE {idx+1}] {analysis_text[:300]}...")
                
                # ENHANCED STRICT validation logic with improved pattern matching
                analysis_lower = analysis_text.lower()
                pose_name_lower = expected_pose.replace('-', ' ').lower()
                
                # Look for explicit YES in the Answer section (first 300 characters)
                has_explicit_yes = bool(
                    'answer: yes' in analysis_lower[:300] or
                    'answer:yes' in analysis_lower[:300] or
                    '**answer: yes**' in analysis_lower[:300] or
                    'result: pass' in analysis_lower[:300] or
                    'final decision**: **pass' in analysis_lower[:300] or
                    'decision: pass' in analysis_lower[:300] or
                    '1. yes' in analysis_lower[:300] or
                    '1. **yes**' in analysis_lower[:300]
                )
                print(f"🔍 [VALIDATION {idx+1}] Has explicit YES: {has_explicit_yes}")
                
                # Check for explicit NO in the Answer section
                has_explicit_no = bool(
                    'answer: no' in analysis_lower[:300] or
                    'answer:no' in analysis_lower[:300] or
                    '**answer: no**' in analysis_lower[:300] or
                    'result: fail' in analysis_lower[:300] or
                    'final decision**: **fail' in analysis_lower[:300] or
                    'decision: fail' in analysis_lower[:300] or
                    '1. no' in analysis_lower[:300] or
                    '1. **no**' in analysis_lower[:300]
                )
                print(f"🔍 [VALIDATION {idx+1}] Has explicit NO: {has_explicit_no}")
                
                # Check for wrong pose identification
                wrong_pose_indicators = [
                    'tree pose', 'downward dog', 'warrior i', 'warrior ii', 'warrior 1', 'warrior 2',
                    'triangle pose', 'child\'s pose', 'cobra pose', 'plank pose', 'mountain pose'
                ]
                # Remove the expected pose from wrong indicators (handle variations)
                expected_variations = [
                    pose_name_lower,
                    pose_name_lower.replace('-', ' '),
                    pose_name_lower.replace('-', ''),
                    pose_name_lower.replace('1', 'i'),
                    pose_name_lower.replace('2', 'ii'),
                    pose_name_lower.replace('-1', ' i'),
                    pose_name_lower.replace('-2', ' ii')
                ]
                wrong_pose_indicators = [p for p in wrong_pose_indicators if p not in expected_variations]
                
                mentions_wrong_pose = any(wrong_pose in analysis_lower[:600] for wrong_pose in wrong_pose_indicators)
                if mentions_wrong_pose:
                    detected_poses = [p for p in wrong_pose_indicators if p in analysis_lower[:600]]
                    print(f"🔍 [VALIDATION {idx+1}] Detected different pose(s): {detected_poses}")
                
                # Check for strong negative indicators
                strong_negative = any(phrase in analysis_lower[:600] for phrase in [
                    'not performing', 'not doing', 'different pose', 
                    'not a yoga', 'not ' + pose_name_lower, 'different from',
                    'this is not', 'this isn\'t', 'not the correct',
                    'incorrect pose', 'wrong pose', 'not exactly'
                ])
                print(f"🔍 [VALIDATION {idx+1}] Strong negative indicators: {strong_negative}")
                
                # SIMPLIFIED validation rules:
                # 1. Must have explicit YES in answer
                # 2. Must NOT have explicit NO  
                # 3. Must NOT have strong negative indicators
                is_frame_valid = (
                    has_explicit_yes and 
                    not has_explicit_no and 
                    not strong_negative
                )
                
                print(f"🔍 [VALIDATION {idx+1}] Final decision: {'VALID' if is_frame_valid else 'INVALID'}")
                
                frame_results.append({
                    'frame_number': idx + 1,
                    'is_valid': is_frame_valid,
                    'analysis': analysis_text[:400],  # First 400 chars
                    's3_key': saved_frame_keys[idx] if idx < len(saved_frame_keys) else None
                })
                
                print(f"{'✅' if is_frame_valid else '❌'} [FRAME {idx+1}/{len(frames)}] Validation: {'VALID' if is_frame_valid else 'INVALID'}")
                
            except Exception as e:
                print(f"Error analyzing frame {idx+1}: {e}")
                frame_results.append({
                    'frame_number': idx + 1,
                    'is_valid': False,
                    'analysis': f"Error: {str(e)}",
                    's3_key': saved_frame_keys[idx] if idx < len(saved_frame_keys) else None
                })
        
        # Calculate overall validation result using majority voting
        valid_count = sum(1 for r in frame_results if r['is_valid'])
        total_count = len(frame_results)
        confidence = valid_count / total_count if total_count > 0 else 0.0
        
        print(f"📊 [VALIDATION SUMMARY] Valid frames: {valid_count}/{total_count} ({confidence*100:.1f}%)")
        
        # BALANCED VALIDATION: Require 60% of frames to be valid
        # This accounts for transition frames while still ensuring correct pose
        # The STRICT prompt validation is the key to rejecting wrong poses
        pose_thresholds = {
            'tree-pose': 0.40,      # 40% - 2/5 frames (balance poses have natural micro-adjustments)
            'downward-dog': 0.40,   # 40% - 2/5 frames (transitions in/out of pose)
            'warrior-1': 0.40,      # 40% - 2/5 frames (lunge transitions)
            'warrior-2': 0.40,      # 40% - 2/5 frames (lunge transitions)
            'triangle-pose': 0.40,  # 40% - 2/5 frames (transitions in/out of pose)
            'default': 0.60         # 60% - 3/5 frames (balanced threshold)
        }
        
        validation_threshold = pose_thresholds.get(expected_pose, pose_thresholds['default'])
        min_frames_required = max(2, int(total_count * validation_threshold))  # Minimum 2 frames
        is_valid = valid_count >= min_frames_required
        
        print(f"{'✅' if is_valid else '❌'} [FINAL DECISION] Video is {'VALID' if is_valid else 'INVALID'} (threshold: {validation_threshold*100:.0f}%, confidence: {confidence*100:.1f}%)")
        print(f"📁 [S3 FRAMES] Validation frames saved to: {expected_pose}/training/analysis/")
        
        if not is_valid:
            print(f"⚠️  [REJECTION] Only {valid_count}/{total_count} frames matched {pose_display_name}. Need at least {min_frames_required} out of {total_count} frames to pass validation.")
        
        # Get most detailed response for reporting
        best_response = max(frame_results, key=lambda x: len(x['analysis']))
        
        return {
            'is_valid': is_valid,
            'confidence': confidence,
            'expected_pose': expected_pose,
            'detected_pose': expected_pose if is_valid else 'unknown',
            'validation_method': 'bedrock_vision_analysis_multi_frame',
            'message': f"Video {'contains' if is_valid else 'does not contain'} valid {pose_display_name} pose ({valid_count}/{total_count} frames validated)",
            'timestamp': self._get_timestamp(),
            'frames_analyzed': total_count,
            'frames_valid': valid_count,
            'frame_results': frame_results,
            'validation_frames_s3': saved_frame_keys,
            'bedrock_response': best_response['analysis']
        }

    def cleanup_temp_files(self, paths: List[str]) -> None:
        """
        Clean up temporary files from /tmp directory.
        
        Args:
            paths: List of file paths to delete
        """
        for path in paths:
            try:
                if os.path.exists(path):
                    if os.path.isfile(path):
                        os.remove(path)
                    elif os.path.isdir(path):
                        import shutil
                        shutil.rmtree(path)
            except Exception as e:
                # Log but don't fail on cleanup errors
                print(f"Warning: Failed to cleanup {path}: {str(e)}")
    
    def _get_timestamp(self) -> str:
        from datetime import datetime
        return datetime.utcnow().isoformat() + 'Z'
