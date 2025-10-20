"""Training video processing tool"""

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
def process_training_video(pose_name: str, video_s3_key: str) -> dict:
    """
    Process a training video to create a golden standard for a yoga pose.
    
    Args:
        pose_name: Name of the yoga pose (downward-dog, warrior-1, warrior-2, tree-pose, triangle-pose)
        video_s3_key: S3 key of the training video
    
    Returns:
        dict: Processing results including golden standard location
    """
    request_id = f"train_{int(time.time())}"
    start_time = time.time()
    
    logger.info(f"🎬 [{request_id}] Processing training video: {pose_name}")
    
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
            FunctionName=os.getenv("TRAINING_LAMBDA_ARN", "yoga-training-lambda"),
            InvocationType='RequestResponse',
            Payload=json.dumps(event)
        )
        
        result = json.loads(response['Payload'].read())
        total_time = time.time() - start_time
        
        if result.get('statusCode') == 200:
            body = json.loads(result['body'])
            logger.info(f"✅ [{request_id}] Training completed in {total_time:.2f}s")
            
            return {
                "status": "success",
                "pose_name": pose_name,
                "video_s3_key": video_s3_key,
                "golden_standard_key": body.get('golden_standard_key'),
                "frames_processed": body.get('frames_processed'),
                "message": body.get('message'),
                "processing_time": total_time
            }
        else:
            error_body = json.loads(result.get('body', '{}'))
            return {
                "status": "error",
                "message": error_body.get('message', 'Training failed'),
                "processing_time": total_time
            }
            
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"💥 [{request_id}] Training failed")
        return {
            "status": "error",
            "message": str(e),
            "processing_time": total_time
        }
