"""
Simple DTW (Dynamic Time Warping) implementation without external dependencies.
Pure Python implementation for Lambda compatibility.
"""

import numpy as np
from typing import List


def dtw_distance(seq1: List[float], seq2: List[float]) -> float:
    """
    Calculate DTW distance between two sequences.
    
    Args:
        seq1: First sequence of values
        seq2: Second sequence of values
    
    Returns:
        DTW distance (lower is better match)
    """
    # Convert to 1D numpy arrays if needed
    seq1 = np.asarray(seq1).flatten()
    seq2 = np.asarray(seq2).flatten()
    
    n, m = len(seq1), len(seq2)
    
    # Create cost matrix
    dtw_matrix = np.full((n + 1, m + 1), np.inf)
    dtw_matrix[0, 0] = 0
    
    # Fill the cost matrix
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(seq1[i-1] - seq2[j-1])
            dtw_matrix[i, j] = cost + min(
                dtw_matrix[i-1, j],      # insertion
                dtw_matrix[i, j-1],      # deletion
                dtw_matrix[i-1, j-1]     # match
            )
    
    return float(dtw_matrix[n, m])


def normalized_dtw_distance(seq1: List[float], seq2: List[float]) -> float:
    """
    Calculate normalized DTW distance (0-1 range).
    
    Args:
        seq1: First sequence of values
        seq2: Second sequence of values
    
    Returns:
        Normalized DTW distance
    """
    distance = dtw_distance(seq1, seq2)
    # Normalize by path length
    path_length = len(seq1) + len(seq2)
    return distance / path_length if path_length > 0 else 0.0


def dtw_score(seq1: List[float], seq2: List[float], max_angle_diff: float = 180.0) -> float:
    """
    Convert DTW distance to a score (0-100).
    
    Args:
        seq1: First sequence of angle values
        seq2: Second sequence of angle values
        max_angle_diff: Maximum possible angle difference (default: 180 degrees)
    
    Returns:
        Score from 0-100 (higher is better)
    """
    if not seq1 or not seq2:
        return 0.0
    
    # Calculate normalized DTW distance
    norm_distance = normalized_dtw_distance(seq1, seq2)
    
    # Convert to score (0-100)
    # Lower distance = higher score
    score = max(0.0, 100.0 - (norm_distance / max_angle_diff) * 100.0)
    
    return score
