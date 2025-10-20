"""Yoga Evaluator Agent - Strands + AgentCore Implementation"""

from strands import Agent
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp
import json
import time
import logging
import os
from tools.training_tool import process_training_video
from tools.evaluation_tool import evaluate_test_video
from logging_config import setup_logging
from dotenv import load_dotenv

load_dotenv()

# Setup logging
setup_logging()

# Configuration
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
BEDROCK_MODEL = os.getenv("BEDROCK_MODEL", "us.anthropic.claude-3-5-sonnet-20241022-v2:0")

logger = logging.getLogger(__name__)
logger.info("=== Yoga Evaluator Agent Starting ===")

app = BedrockAgentCoreApp()

# Initialize Bedrock model
logger.info(f"Initializing Bedrock model: {BEDROCK_MODEL}")
try:
    model = BedrockModel(model_id=BEDROCK_MODEL)
    logger.info("✅ Bedrock model initialized successfully")
except Exception as e:
    logger.error(f"❌ Failed to initialize Bedrock model: {e}")
    raise

# Create agent with tools
logger.info("Creating Yoga Evaluator Agent...")
agent = Agent(
    model=model,
    tools=[process_training_video, evaluate_test_video],
    system_prompt="""
You are a Yoga Pose Evaluation Specialist AI.

Your role is to help users process and evaluate their yoga videos using computer vision and pose analysis.

SUPPORTED POSES:
- downward-dog (Downward Facing Dog)
- warrior-1 (Warrior I)
- warrior-2 (Warrior II)
- tree-pose (Tree Pose)
- triangle-pose (Triangle Pose)

WORKFLOW:
1. For TRAINING videos: Use process_training_video to create a golden standard
2. For TESTING videos: Use evaluate_test_video to compare against the golden standard

When a user uploads a video:
1. Confirm the pose name
2. Determine if it's a training or testing video
3. Call the appropriate tool with the pose name and S3 key
4. Return the tool result as JSON followed by a human-readable explanation

RESPONSE FORMAT:
Always return the complete tool result as JSON at the start of your response, followed by explanation.

Example for training:
{"status": "success", "frames_processed": 145, "processing_time": 42.3, "golden_standard_key": "tree-pose/training/golden-standard.json", "message": "Training completed"}

Then provide your explanation...

Example for evaluation:
{"status": "success", "overall_score": 87, "angle_scores": {"left_knee": 92, "right_hip": 83}, "frames_processed": 98, "processing_time": 35.1}

Then provide your feedback...

IMPORTANT:
- Always include the complete JSON result from the tool
- Explain scores in simple terms
- Provide specific feedback on angles that need improvement
- Be encouraging and supportive

Be friendly, clear, and helpful!
"""
)
logger.info("✅ Agent created with 2 tools")

@app.entrypoint
def yoga_evaluator(payload):
    """
    Main entrypoint for yoga evaluation
    """
    request_id = f"req_{int(time.time())}"
    start_time = time.time()
    
    logger.info(f"🚀 [{request_id}] New yoga evaluation request")
    
    try:
        user_prompt = payload.get("prompt", "")
        
        if not user_prompt:
            return {
                "status": "error",
                "message": "No prompt provided",
                "request_id": request_id
            }
        
        logger.info(f"📝 [{request_id}] Processing: {user_prompt[:100]}...")
        
        # Process with agent
        response = agent(user_prompt)
        
        # Parse response
        content = response.message.get('content', [{}])
        result_text = content[0].get('text', '') if content else ''
        
        if not result_text:
            return {
                "status": "error",
                "message": "Empty response from agent",
                "request_id": request_id
            }
        
        # Try to parse as JSON, fallback to text
        try:
            parsed_result = json.loads(result_text)
            result = {
                "status": "success",
                "request_id": request_id,
                "duration": time.time() - start_time,
                **parsed_result
            }
        except json.JSONDecodeError:
            result = {
                "status": "success",
                "message": result_text,
                "request_id": request_id,
                "duration": time.time() - start_time
            }
        
        total_time = time.time() - start_time
        logger.info(f"🎉 [{request_id}] Request completed in {total_time:.2f}s")
        return result
        
    except Exception as e:
        total_time = time.time() - start_time
        logger.exception(f"💥 [{request_id}] Request failed")
        return {
            "status": "error",
            "message": str(e),
            "request_id": request_id,
            "duration": total_time
        }

if __name__ == "__main__":
    logger.info("🚀 Starting Bedrock AgentCore App...")
    
    try:
        logger.info(f"🌍 AWS Region: {AWS_REGION}")
        logger.info("🧘 Yoga Evaluator Agent ready!")
        logger.info("📡 Waiting for requests...")
        
        app.run()
        
    except KeyboardInterrupt:
        logger.info("⏹️ Stopped by user")
    except Exception as e:
        logger.exception(f"💥 Startup failed: {e}")
        raise
    finally:
        logger.info("🏁 Shutdown complete")
