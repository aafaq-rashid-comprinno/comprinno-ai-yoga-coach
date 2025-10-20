"""
YogaPoseAnalyzer - Core pose analysis and evaluation logic.

This module provides the main pose analysis functionality for the Yoga Evaluation System,
including pose detection, angle calculation, golden standard creation, and evaluation.
"""

import math
import numpy as np
from typing import Dict, List, Optional, Tuple
import mediapipe as mp
from datetime import datetime


class YogaPoseAnalyzer:
    """
    Analyzes yoga poses using MediaPipe pose detection and angle calculations.
    
    Supports multiple yoga poses with pose-specific angle definitions and tolerances.
    """
    
    # Yoga pose angle definitions - defines which angles to track for each pose
    POSE_ANGLE_DEFINITIONS = {
        'downward-dog': {
            'angles': [
                'left_shoulder', 'right_shoulder',
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'spine_alignment'
            ],
            'tolerances': {
                'left_shoulder': 15,
                'right_shoulder': 15,
                'left_hip': 20,
                'right_hip': 20,
                'left_knee': 10,
                'right_knee': 10,
                'spine_alignment': 8
            }
        },
        'warrior-1': {
            'angles': [
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'left_shoulder', 'right_shoulder',
                'spine_alignment'
            ],
            'tolerances': {
                'left_hip': 25,
                'right_hip': 25,
                'left_knee': 15,
                'right_knee': 15,
                'left_shoulder': 20,
                'right_shoulder': 20,
                'spine_alignment': 10
            }
        },
        'warrior-2': {
            'angles': [
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'left_shoulder', 'right_shoulder',
                'left_elbow', 'right_elbow'
            ],
            'tolerances': {
                'left_hip': 25,
                'right_hip': 25,
                'left_knee': 15,
                'right_knee': 15,
                'left_shoulder': 20,
                'right_shoulder': 20,
                'left_elbow': 10,
                'right_elbow': 10
            }
        },
        'tree-pose': {
            'angles': [
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'left_shoulder', 'right_shoulder',
                'spine_alignment'
            ],
            'tolerances': {
                'left_hip': 20,
                'right_hip': 20,
                'left_knee': 25,
                'right_knee': 25,
                'left_shoulder': 15,
                'right_shoulder': 15,
                'spine_alignment': 12
            }
        },
        'triangle-pose': {
            'angles': [
                'left_hip', 'right_hip',
                'left_knee', 'right_knee',
                'left_shoulder', 'right_shoulder',
                'spine_alignment'
            ],
            'tolerances': {
                'left_hip': 20,
                'right_hip': 20,
                'left_knee': 10,
                'right_knee': 10,
                'left_shoulder': 25,
                'right_shoulder': 25,
                'spine_alignment': 15
            }
        }
    }
    
    # MediaPipe landmark indices for angle calculations
    LANDMARK_INDICES = {
        'nose': 0,
        'left_shoulder': 11,
        'right_shoulder': 12,
        'left_elbow': 13,
        'right_elbow': 14,
        'left_wrist': 15,
        'right_wrist': 16,
        'left_hip': 23,
        'right_hip': 24,
        'left_knee': 25,
        'right_knee': 26,
        'left_ankle': 27,
        'right_ankle': 28
    }
    
    def __init__(self, pose_name: str, visibility_threshold: float = 0.3):
        """
        Initialize YogaPoseAnalyzer with pose-specific configuration.
        
        OPTIMIZED: Lowered default threshold from 0.5 to 0.3 for better pose detection
        Target: Detect poses in 80%+ of frames (vs previous 13.8%)
        
        Args:
            pose_name: Name of the yoga pose (e.g., 'downward-dog')
            visibility_threshold: Minimum visibility score for reliable landmarks (0.0-1.0, default: 0.3)
        
        Raises:
            ValueError: If pose_name is not supported
        """
        if pose_name not in self.POSE_ANGLE_DEFINITIONS:
            raise ValueError(
                f"Unsupported pose: {pose_name}. "
                f"Supported poses: {list(self.POSE_ANGLE_DEFINITIONS.keys())}"
            )
        
        self.pose_name = pose_name
        self.visibility_threshold = visibility_threshold
        self.angle_config = self.POSE_ANGLE_DEFINITIONS[pose_name]
        
        # Initialize MediaPipe Pose with Lambda-optimized settings
        self.mp_pose = mp.solutions.pose
        self.pose_detector = self.mp_pose.Pose(
            static_image_mode=True,  # Process each frame independently
            model_complexity=1,  # Balance between accuracy and speed (0, 1, or 2)
            smooth_landmarks=False,  # No smoothing needed for static images
            enable_segmentation=False,  # Disable segmentation to save memory
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5
        )

    def detect_pose_landmarks(self, frame: np.ndarray) -> Optional[Dict]:
        """
        Detect pose landmarks in a frame using MediaPipe.
        
        Args:
            frame: Input frame as numpy array (BGR format from OpenCV)
        
        Returns:
            Dictionary containing landmarks and visibility scores, or None if detection fails
        """
        # Convert BGR to RGB for MediaPipe
        frame_rgb = frame.copy()
        if len(frame.shape) == 3 and frame.shape[2] == 3:
            frame_rgb = frame[:, :, ::-1]  # BGR to RGB
        
        # Process frame with MediaPipe
        results = self.pose_detector.process(frame_rgb)
        
        if not results.pose_landmarks:
            return None
        
        # Extract landmarks with visibility scores
        landmarks = {}
        for name, idx in self.LANDMARK_INDICES.items():
            landmark = results.pose_landmarks.landmark[idx]
            landmarks[name] = {
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            }
        
        return landmarks
    
    def _calculate_angle(self, point1: Dict, point2: Dict, point3: Dict) -> Optional[float]:
        """
        Calculate angle between three points (point2 is the vertex).
        
        Args:
            point1, point2, point3: Landmark dictionaries with x, y, z coordinates
        
        Returns:
            Angle in degrees, or None if calculation fails
        """
        try:
            # Create vectors
            vector1 = np.array([
                point1['x'] - point2['x'],
                point1['y'] - point2['y'],
                point1['z'] - point2['z']
            ])
            vector2 = np.array([
                point3['x'] - point2['x'],
                point3['y'] - point2['y'],
                point3['z'] - point2['z']
            ])
            
            # Calculate angle using dot product
            cos_angle = np.dot(vector1, vector2) / (
                np.linalg.norm(vector1) * np.linalg.norm(vector2)
            )
            
            # Clamp to valid range to avoid numerical errors
            cos_angle = np.clip(cos_angle, -1.0, 1.0)
            
            angle = math.degrees(math.acos(cos_angle))
            return angle
            
        except (ZeroDivisionError, ValueError):
            return None
    
    def _check_landmarks_visible(self, landmarks: Dict, landmark_names: List[str]) -> bool:
        """
        Check if all specified landmarks meet visibility threshold.
        
        Args:
            landmarks: Dictionary of detected landmarks with visibility scores
            landmark_names: List of landmark names to check
        
        Returns:
            True if all landmarks are visible above threshold, False otherwise
        """
        for name in landmark_names:
            if name not in landmarks:
                return False
            if landmarks[name]['visibility'] < self.visibility_threshold:
                return False
        return True
    
    def calculate_angles(self, landmarks: Dict) -> Dict[str, float]:
        """
        Calculate all relevant joint angles for the current pose.
        
        OPTIMIZED: Check visibility per angle instead of all-or-nothing.
        This allows partial angle data when some landmarks are occluded.
        
        Args:
            landmarks: Dictionary of detected landmarks with visibility scores
        
        Returns:
            Dictionary mapping angle names to angle values (in degrees)
            Returns partial angles if some landmarks are not visible
        """
        angles = {}
        
        # OPTIMIZED: Calculate each angle independently based on landmark visibility
        # Previous: Returned empty dict if ANY landmark was below threshold
        # Current: Calculate angles for visible landmarks only
        
        # Calculate shoulder angles (shoulder-elbow-wrist)
        if 'left_shoulder' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['left_shoulder', 'left_elbow', 'left_wrist']):
                angle = self._calculate_angle(
                    landmarks['left_shoulder'],
                    landmarks['left_elbow'],
                    landmarks['left_wrist']
                )
                if angle is not None:
                    angles['left_shoulder'] = angle
        
        if 'right_shoulder' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['right_shoulder', 'right_elbow', 'right_wrist']):
                angle = self._calculate_angle(
                    landmarks['right_shoulder'],
                    landmarks['right_elbow'],
                    landmarks['right_wrist']
                )
                if angle is not None:
                    angles['right_shoulder'] = angle
        
        # Calculate hip angles (shoulder-hip-knee)
        if 'left_hip' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['left_shoulder', 'left_hip', 'left_knee']):
                angle = self._calculate_angle(
                    landmarks['left_shoulder'],
                    landmarks['left_hip'],
                    landmarks['left_knee']
                )
                if angle is not None:
                    angles['left_hip'] = angle
        
        if 'right_hip' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['right_shoulder', 'right_hip', 'right_knee']):
                angle = self._calculate_angle(
                    landmarks['right_shoulder'],
                    landmarks['right_hip'],
                    landmarks['right_knee']
                )
                if angle is not None:
                    angles['right_hip'] = angle
        
        # Calculate knee angles (hip-knee-ankle)
        if 'left_knee' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['left_hip', 'left_knee', 'left_ankle']):
                angle = self._calculate_angle(
                    landmarks['left_hip'],
                    landmarks['left_knee'],
                    landmarks['left_ankle']
                )
                if angle is not None:
                    angles['left_knee'] = angle
        
        if 'right_knee' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['right_hip', 'right_knee', 'right_ankle']):
                angle = self._calculate_angle(
                    landmarks['right_hip'],
                    landmarks['right_knee'],
                    landmarks['right_ankle']
                )
                if angle is not None:
                    angles['right_knee'] = angle
        
        # Calculate elbow angles (shoulder-elbow-wrist)
        if 'left_elbow' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['left_shoulder', 'left_elbow', 'left_wrist']):
                angle = self._calculate_angle(
                    landmarks['left_shoulder'],
                    landmarks['left_elbow'],
                    landmarks['left_wrist']
                )
                if angle is not None:
                    angles['left_elbow'] = angle
        
        if 'right_elbow' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['right_shoulder', 'right_elbow', 'right_wrist']):
                angle = self._calculate_angle(
                    landmarks['right_shoulder'],
                    landmarks['right_elbow'],
                    landmarks['right_wrist']
                )
                if angle is not None:
                    angles['right_elbow'] = angle
        
        # Calculate spine alignment (hip-shoulder-nose angle)
        if 'spine_alignment' in self.angle_config['angles']:
            if self._check_landmarks_visible(landmarks, ['left_hip', 'right_hip', 'left_shoulder', 'right_shoulder', 'nose']):
                # Use midpoint of hips and shoulders for spine alignment
                mid_hip_x = (landmarks['left_hip']['x'] + landmarks['right_hip']['x']) / 2
                mid_hip_y = (landmarks['left_hip']['y'] + landmarks['right_hip']['y']) / 2
                mid_hip_z = (landmarks['left_hip']['z'] + landmarks['right_hip']['z']) / 2
                
                mid_shoulder_x = (landmarks['left_shoulder']['x'] + landmarks['right_shoulder']['x']) / 2
                mid_shoulder_y = (landmarks['left_shoulder']['y'] + landmarks['right_shoulder']['y']) / 2
                mid_shoulder_z = (landmarks['left_shoulder']['z'] + landmarks['right_shoulder']['z']) / 2
                
                mid_hip = {'x': mid_hip_x, 'y': mid_hip_y, 'z': mid_hip_z}
                mid_shoulder = {'x': mid_shoulder_x, 'y': mid_shoulder_y, 'z': mid_shoulder_z}
                
                angle = self._calculate_angle(
                    mid_hip,
                    mid_shoulder,
                    landmarks['nose']
                )
                if angle is not None:
                    angles['spine_alignment'] = angle
        
        return angles
    
    def __del__(self):
        """Clean up MediaPipe resources."""
        if hasattr(self, 'pose_detector'):
            self.pose_detector.close()

    def create_golden_standard(
        self,
        angle_data: List[Dict[str, float]],
        video_source: str,
        metadata: Optional[Dict] = None
    ) -> Dict:
        """
        Create golden standard by aggregating angle data from multiple frames.
        
        Args:
            angle_data: List of angle dictionaries from each frame
            video_source: Name of the source video file
            metadata: Optional metadata to include in golden standard
        
        Returns:
            Golden standard dictionary with statistics for each angle
        """
        if not angle_data:
            raise ValueError("Cannot create golden standard from empty angle data")
        
        # Initialize aggregation structure
        angle_aggregates = {}
        
        # Get all unique angle names from the data
        all_angle_names = set()
        for frame_angles in angle_data:
            all_angle_names.update(frame_angles.keys())
        
        # Aggregate data for each angle
        for angle_name in all_angle_names:
            # Collect all values for this angle across frames
            values = [
                frame_angles[angle_name]
                for frame_angles in angle_data
                if angle_name in frame_angles
            ]
            
            if not values:
                continue
            
            # Calculate statistics
            values_array = np.array(values)
            angle_aggregates[angle_name] = {
                'mean': float(np.mean(values_array)),
                'std': float(np.std(values_array)),
                'min': float(np.min(values_array)),
                'max': float(np.max(values_array)),
                'count': len(values),
                'confidence': len(values) / len(angle_data)  # Ratio of frames with this angle
            }
        
        # Build golden standard structure
        # UPDATED: Added angle_sequences for DTW analysis
        golden_standard = {
            'pose_name': self.pose_name,
            'created_at': datetime.utcnow().isoformat() + 'Z',
            'video_source': video_source,
            'total_frames': len(angle_data),
            'angles': angle_aggregates,
            'angle_sequences': angle_data,  # NEW: Store raw sequences for DTW
            'metadata': metadata or {}
        }
        
        return golden_standard

    def evaluate_with_dtw(
        self,
        test_angles: List[Dict[str, float]],
        golden_angles: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Evaluate test angles using DTW (Dynamic Time Warping) for temporal sequence analysis.
        
        DTW handles timing variations and speed differences between test and golden sequences.
        
        Args:
            test_angles: List of angle dictionaries from test video (frame-by-frame)
            golden_angles: List of angle dictionaries from golden standard (frame-by-frame)
        
        Returns:
            Dictionary mapping angle names to DTW-based scores (0-100)
        """
        dtw_scores = {}
        
        # Get all angle names from the configuration
        for angle_name in self.angle_config['angles']:
            # Extract sequences for this angle
            test_seq = [
                frame.get(angle_name, None)
                for frame in test_angles
            ]
            golden_seq = [
                frame.get(angle_name, None)
                for frame in golden_angles
            ]
            
            # Filter out None values
            test_seq = [val for val in test_seq if val is not None]
            golden_seq = [val for val in golden_seq if val is not None]
            
            # Skip if insufficient data
            if len(test_seq) < 3 or len(golden_seq) < 3:
                print(f"⚠️  [DTW] Skipping {angle_name}: insufficient data (test:{len(test_seq)}, golden:{len(golden_seq)})")
                continue
            
            # Calculate DTW score
            score = dtw_score(test_seq, golden_seq, max_angle_diff=180.0)
            dtw_scores[angle_name] = score
            
            print(f"🔬 [DTW] {angle_name}: {score:.1f} (test_len:{len(test_seq)}, golden_len:{len(golden_seq)})")
        
        return dtw_scores

    def evaluate_angles(
        self,
        test_angles: List[Dict[str, float]],
        golden_standard: Dict
    ) -> Dict:
        """
        Evaluate test angles against golden standard and calculate scores.
        
        UPDATED: Now includes DTW-based sequence analysis in addition to mean-based evaluation.
        Combines both scores: 70% mean-based + 30% DTW-based for final score.
        
        Args:
            test_angles: List of angle dictionaries from test video frames
            golden_standard: Golden standard dictionary with angle statistics
        
        Returns:
            Evaluation dictionary with per-angle scores and overall score
        """
        if not test_angles:
            raise ValueError("Cannot evaluate empty test angles")
        
        if 'angles' not in golden_standard:
            raise ValueError("Invalid golden standard: missing 'angles' key")
        
        # Calculate mean angles from test data
        test_angle_means = {}
        for angle_name in golden_standard['angles'].keys():
            values = [
                frame_angles[angle_name]
                for frame_angles in test_angles
                if angle_name in frame_angles
            ]
            if values:
                test_angle_means[angle_name] = np.mean(values)
        
        # NEW: Calculate DTW scores if angle sequences are available
        dtw_scores = {}
        if 'angle_sequences' in golden_standard and golden_standard['angle_sequences']:
            print(f"🔬 [DTW] Calculating DTW scores for temporal sequence analysis...")
            dtw_scores = self.evaluate_with_dtw(test_angles, golden_standard['angle_sequences'])
            print(f"🔬 [DTW] Calculated DTW scores for {len(dtw_scores)} angles")
        else:
            print(f"⚠️  [DTW] No angle sequences in golden standard, skipping DTW analysis")
        
        # Evaluate each angle
        angle_evaluations = {}
        total_score = 0.0
        total_weight = 0.0
        
        for angle_name, golden_stats in golden_standard['angles'].items():
            if angle_name not in test_angle_means:
                # Skip angles not detected in test video
                continue
            
            test_mean = test_angle_means[angle_name]
            golden_mean = golden_stats['mean']
            tolerance = self.angle_config['tolerances'].get(angle_name, 15)
            
            # Calculate deviation
            deviation = test_mean - golden_mean
            abs_deviation = abs(deviation)
            
            # Calculate score (0-100) based on deviation and tolerance
            if abs_deviation <= tolerance:
                # Within tolerance: score based on how close to ideal
                score = 100 - (abs_deviation / tolerance) * 30  # Max 30 points deduction
            else:
                # Outside tolerance: score decreases more rapidly
                excess_deviation = abs_deviation - tolerance
                score = 70 - (excess_deviation / tolerance) * 70  # Up to 70 more points deduction
                score = max(0, score)  # Floor at 0
            
            # Determine status
            if score >= 85:
                status = "EXCELLENT"
            elif score >= 70:
                status = "GOOD"
            elif score >= 50:
                status = "NEEDS_IMPROVEMENT"
            else:
                status = "POOR"
            
            # NEW: Get DTW score for this angle if available
            dtw_score = dtw_scores.get(angle_name, None)
            
            # NEW: Calculate combined score (70% mean-based + 30% DTW)
            if dtw_score is not None:
                combined_score = score * 0.7 + dtw_score * 0.3
            else:
                combined_score = score  # Fall back to mean-based only
            
            angle_evaluations[angle_name] = {
                'test_mean': float(test_mean),
                'golden_mean': float(golden_mean),
                'deviation': float(deviation),
                'tolerance': float(tolerance),
                'mean_based_score': float(score),  # Original mean-based score
                'dtw_score': float(dtw_score) if dtw_score is not None else None,  # NEW: DTW score
                'combined_score': float(combined_score),  # NEW: Combined score (70% mean + 30% DTW)
                'score': float(combined_score),  # Use combined score as primary
                'status': status
            }
            
            # Weight by confidence from golden standard
            weight = golden_stats.get('confidence', 1.0)
            total_score += combined_score * weight  # Use combined score
            total_weight += weight
        
        # Calculate overall score
        overall_score = total_score / total_weight if total_weight > 0 else 0.0
        
        return {
            'overall_score': float(overall_score),
            'angle_evaluations': angle_evaluations,
            'total_frames': len(test_angles)
        }

    def evaluate_with_dtw(
        self,
        test_angles: List[Dict[str, float]],
        golden_angles: List[Dict[str, float]]
    ) -> Dict[str, float]:
        """
        Use Dynamic Time Warping (DTW) to compare angle sequences over time.
        Handles timing variations and speed differences between test and golden videos.
        
        Args:
            test_angles: List of angle dictionaries from test video frames
            golden_angles: List of angle dictionaries from golden standard video frames
        
        Returns:
            Dictionary mapping angle names to DTW-based scores (0-100)
        """
        if not test_angles or not golden_angles:
            return {}
        
        dtw_scores = {}
        
        # Get all angle names from the configuration
        for angle_name in self.angle_config['angles']:
            # Extract sequences for this angle
            test_seq = [
                frame.get(angle_name, None)
                for frame in test_angles
            ]
            golden_seq = [
                frame.get(angle_name, None)
                for frame in golden_angles
            ]
            
            # Filter out None values
            test_seq = [val for val in test_seq if val is not None]
            golden_seq = [val for val in golden_seq if val is not None]
            
            # Skip if insufficient data (need at least 3 frames)
            if len(test_seq) < 3 or len(golden_seq) < 3:
                continue
            
            try:
                # Use fastdtw for DTW calculation (simple and reliable)
                from fastdtw import fastdtw
                from scipy.spatial.distance import euclidean
                
                # Calculate DTW distance using fastdtw
                distance, path = fastdtw(test_seq, golden_seq, dist=euclidean)
                
                # Normalize by sequence length
                avg_length = (len(test_seq) + len(golden_seq)) / 2
                normalized_distance = distance / avg_length
                
                # Convert to score (0-100)
                max_distance = 30  # Threshold for 0 score
                score = max(0, 100 - (normalized_distance / max_distance) * 100)
                
                dtw_scores[angle_name] = float(score)
                
            except Exception as e:
                # If DTW calculation fails, skip this angle
                print(f"⚠️  [DTW] Failed to calculate DTW for {angle_name}: {e}")
                continue
        
        return dtw_scores

    # Pose-specific feedback templates
    FEEDBACK_TEMPLATES = {
        'left_shoulder': {
            'positive': "Your left shoulder angle is {deviation:.1f}° from ideal, which is within the acceptable range.",
            'negative': "Your left shoulder angle deviates by {deviation:.1f}° from ideal. Try adjusting your arm position.",
            'recommendation': "Focus on shoulder alignment and arm extension."
        },
        'right_shoulder': {
            'positive': "Your right shoulder angle is {deviation:.1f}° from ideal, which is within the acceptable range.",
            'negative': "Your right shoulder angle deviates by {deviation:.1f}° from ideal. Try adjusting your arm position.",
            'recommendation': "Focus on shoulder alignment and arm extension."
        },
        'left_hip': {
            'positive': "Your left hip angle is well-aligned, only {deviation:.1f}° from ideal.",
            'negative': "Your left hip angle deviates by {deviation:.1f}° from ideal. Work on hip flexibility and positioning.",
            'recommendation': "Practice hip opening exercises and focus on proper hip alignment."
        },
        'right_hip': {
            'positive': "Your right hip angle is well-aligned, only {deviation:.1f}° from ideal.",
            'negative': "Your right hip angle deviates by {deviation:.1f}° from ideal. Work on hip flexibility and positioning.",
            'recommendation': "Practice hip opening exercises and focus on proper hip alignment."
        },
        'left_knee': {
            'positive': "Your left knee alignment is good, within {deviation:.1f}° of ideal.",
            'negative': "Your left knee angle is off by {deviation:.1f}°. Ensure proper knee alignment to avoid injury.",
            'recommendation': "Keep your knee aligned over your ankle and avoid hyperextension."
        },
        'right_knee': {
            'positive': "Your right knee alignment is good, within {deviation:.1f}° of ideal.",
            'negative': "Your right knee angle is off by {deviation:.1f}°. Ensure proper knee alignment to avoid injury.",
            'recommendation': "Keep your knee aligned over your ankle and avoid hyperextension."
        },
        'left_elbow': {
            'positive': "Your left elbow position is correct, only {deviation:.1f}° from ideal.",
            'negative': "Your left elbow angle deviates by {deviation:.1f}°. Adjust your arm extension.",
            'recommendation': "Focus on maintaining straight or properly bent arms as required by the pose."
        },
        'right_elbow': {
            'positive': "Your right elbow position is correct, only {deviation:.1f}° from ideal.",
            'negative': "Your right elbow angle deviates by {deviation:.1f}°. Adjust your arm extension.",
            'recommendation': "Focus on maintaining straight or properly bent arms as required by the pose."
        },
        'spine_alignment': {
            'positive': "Your spine alignment is excellent, only {deviation:.1f}° from ideal.",
            'negative': "Your spine alignment needs improvement, deviating by {deviation:.1f}°. Focus on lengthening your spine.",
            'recommendation': "Engage your core and focus on maintaining a neutral spine throughout the pose."
        }
    }
    
    def generate_feedback(
        self,
        evaluation: Dict,
        video_source: str,
        pass_threshold: float = 70.0
    ) -> Dict:
        """
        Generate human-readable feedback from evaluation results.
        
        Args:
            evaluation: Evaluation dictionary from evaluate_angles()
            video_source: Name of the test video file
            pass_threshold: Minimum score to pass (default: 70.0)
        
        Returns:
            Complete evaluation result with feedback and recommendations
        """
        overall_score = evaluation['overall_score']
        angle_evaluations = evaluation['angle_evaluations']
        
        # Determine grade based on score
        if overall_score >= 90:
            grade = "A"
        elif overall_score >= 80:
            grade = "B"
        elif overall_score >= 70:
            grade = "C"
        elif overall_score >= 60:
            grade = "D"
        else:
            grade = "F"
        
        # Determine pass/fail
        pass_fail = "PASS" if overall_score >= pass_threshold else "FAIL"
        
        # Generate detailed feedback for each angle
        detailed_feedback = {}
        recommendations = []
        
        for angle_name, angle_eval in angle_evaluations.items():
            abs_deviation = abs(angle_eval['deviation'])
            status = angle_eval['status']
            
            # Get feedback template
            template = self.FEEDBACK_TEMPLATES.get(angle_name, {
                'positive': "Your {angle} is {deviation:.1f}° from ideal.",
                'negative': "Your {angle} deviates by {deviation:.1f}° from ideal.",
                'recommendation': "Focus on proper alignment for this angle."
            })
            
            # Generate feedback message
            if status in ["EXCELLENT", "GOOD"]:
                feedback_msg = template['positive'].format(deviation=abs_deviation)
            else:
                feedback_msg = template['negative'].format(deviation=abs_deviation)
                # Add recommendation for angles that need improvement
                if template['recommendation'] not in recommendations:
                    recommendations.append(template['recommendation'])
            
            detailed_feedback[angle_name] = {
                **angle_eval,
                'feedback': feedback_msg
            }
        
        # Generate summary feedback
        if overall_score >= 85:
            summary = f"Excellent form! Your {self.pose_name} pose is very well executed."
        elif overall_score >= 70:
            summary = f"Good overall form in your {self.pose_name} pose. Minor adjustments will help perfect it."
        elif overall_score >= 50:
            summary = f"Your {self.pose_name} pose needs some improvement. Focus on the areas highlighted below."
        else:
            summary = f"Your {self.pose_name} pose requires significant work. Review the recommendations carefully."
        
        # Add general recommendations if score is below threshold
        if overall_score < pass_threshold:
            recommendations.append("Consider practicing with a yoga instructor for personalized guidance.")
            recommendations.append("Watch tutorial videos to understand proper form and alignment.")
        
        # Build complete result
        result = {
            'pose_name': self.pose_name,
            'evaluated_at': datetime.utcnow().isoformat() + 'Z',
            'video_source': video_source,
            'overall_score': overall_score,
            'grade': grade,
            'pass_fail': pass_fail,
            'total_frames': evaluation['total_frames'],
            'angle_evaluations': detailed_feedback,
            'summary_feedback': summary,
            'recommendations': recommendations
        }
        
        return result
