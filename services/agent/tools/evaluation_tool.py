"""Test video evaluation tool"""

from strands import tool
import boto3
import json
import time
import logging
import os

logger = logging.getLogger(__name__)

# AWS clients
lambda_client = boto3.client('lambda', region_name=os.getenv("AWS_REGION", "us-east-1"))

@tool
def evaluate_test_video(pose_name: str, video_s3_key: str) -> dict:
    """
    Evaluate a test video against the golden standard for a yoga pose.
    
    Args:
        pose_name: Name of the yoga pose (downward-dog, warrior-1, warrior-2, tree-pose, triangle-pose)
        video_s3_key: S3 key of the test video
    
    Returns:
        dict: Evaluation results including score and feedback
    """
    request_id = f"eval_{int(time.time())}"
    start_time = time.time()
    
    logger.info(f"📊 [{request_id}] Evaluating test video: {pose_name}")
    
    try:
        event = {
            'Records': [{
                's3': {
                    'bucket': {'name': os.getenv("S3_BUCKET", "yoga-eval-bucket-1760638546")},
                    'object': {'key': video_s3_key}
                }
            }]
        }
        
        response = lambda_client.invoke(
            FunctionName=os.getenv("TESTING_LAMBDA_ARN", "yoga-testing-lambda"),
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        total_time = time.time() - start_time
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            logger.info(f"✅ [{request_id}] Evaluation completed in {total_time:.2f}s")
            
            return {
                "status": "success",
                "pose_name": pose_name,
                "video_s3_key": video_s3_key,
                "overall_score": body.get('overall_score'),
                "angle_scores": body.get('angle_scores'),
                "feedback": body.get('feedback'),
                "frames_processed": body.get('frames_processed'),
                "message": body.get('message'),
                "processing_time": total_time
            }
        else:
            error_body = json.loads(result.get('body', '{}'))
            return {
                "status": "error",
                "message": error_body.get('message', 'Evaluation failed'),
                "processing_time": total_time
            }
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"💥 [{request_id}] Evaluation failed")
        return {
            "status": "error",
            "message": str(e),
            "processing_time": total_time
        }
