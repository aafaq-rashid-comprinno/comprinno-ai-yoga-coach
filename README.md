# Comprinno AI Yoga Coach

An AI-powered yoga pose evaluation system that analyzes yoga videos using computer vision and provides personalized feedback through conversational AI agents.

## Architecture

The system consists of three main services:

### 1. Agent Service (`/services/agent`)
- **Purpose**: Conversational AI agent for yoga pose evaluation
- **Framework**: Bedrock AgentCore with Strands framework
- **Models**: Amazon Claude 3.5 Sonnet for validation and feedback

### 2. UI Service (`/services/ui`)
- **Purpose**: Web interface for video upload and results
- **Framework**: Flask web application
- **Port**: 5000
- **Authentication**: AWS Cognito integration

### 3. Lambda Functions (`/lambda_functions`)
- **Purpose**: Serverless video processing pipeline
- **Functions**: Training (golden standard creation) and Testing (evaluation)
- **Triggers**: S3 events for automatic processing
- **Deployment**: Terraform modular infrastructure

## Core Components

### AI Agent Tools (`/services/agent/tools`)

#### 1. Training Tool (`training_tool.py`)
- Creates "golden standard" pose data from expert videos
- Input: Pose name and S3 video key
- Output: Golden standard angle measurements and frame data

#### 2. Evaluation Tool (`evaluation_tool.py`)
- Evaluates user videos against golden standards
- Input: Pose name and S3 video key
- Output: Pose scores, angle analysis, and improvement feedback

### Video Processing Pipeline (`/lambda_functions`)

#### Training Lambda (`training/training_lambda_function.py`)
- Validates videos using Bedrock (5-frame sampling)
- Extracts pose landmarks using MediaPipe
- Creates golden standard angle measurements
- Stores results in S3 for evaluation reference

#### Testing Lambda (`testing/testing_lambda_function.py`)
- Compares user poses against golden standards
- Calculates angle-based scores with pose-specific tolerances
- Uses Dynamic Time Warping for sequence alignment
- Generates detailed feedback and improvement suggestions

### Pose Analysis Engine (`/lambda_functions/shared`)

#### Yoga Pose Analyzer (`yoga_pose_analyzer.py`)
- **Supported Poses**: Downward Dog, Warrior I/II, Tree Pose, Triangle Pose
- **MediaPipe Integration**: 33 body landmarks per frame
- **Angle Calculations**: 7-8 key angles per pose
- **Scoring System**: Pose-specific tolerances (8-25 degrees)

#### Video Processor (`video_processor.py`)
- Frame extraction and sampling optimization
- Bedrock validation with exponential backoff
- Temporary file management and cleanup

## Supported Yoga Poses

### Pose Definitions
- **Downward Dog**: 7 angles (shoulders, hips, knees, spine)
- **Warrior I**: 7 angles (hips, knees, shoulders, spine)
- **Warrior II**: 8 angles (hips, knees, shoulders, elbows)
- **Tree Pose**: 7 angles (hips, knees, shoulders, spine)
- **Triangle Pose**: 7 angles (hips, knees, shoulders, spine)

### Angle Tolerances
- **Strict**: Knees (10-15°), Spine (8-12°)
- **Moderate**: Shoulders (15-20°), Hips (20-25°)
- **Flexible**: Complex poses (up to 25°)

## Configuration

### Environment Variables

#### Agent Service (`.env`)
```bash
# AWS Configuration
AWS_REGION=us-east-1
BEDROCK_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0

# S3 Configuration
S3_BUCKET=yoga-eval-bucket

# Lambda Functions
TRAINING_LAMBDA_ARN=arn:aws:lambda:us-east-1:<account-id>:function:yoga-training-lambda
TESTING_LAMBDA_ARN=arn:aws:lambda:us-east-1:<account-id>:function:yoga-testing-lambda

# Logging
LOG_LEVEL=INFO
```

#### UI Service (`.env`)
```bash
# AWS Configuration
AWS_REGION=us-east-1
BUCKET_NAME=yoga-eval-bucket

# Cognito Authentication
COGNITO_USER_POOL_ID=<your-user-pool-id>
COGNITO_CLIENT_ID=<your-client-id>

# AgentCore Integration
AGENTCORE_ARN=arn:aws:bedrock-agentcore:us-east-1:<account-id>:runtime/yoga_coach-tiHwXqEf7V

# Server Configuration
SERVER_PORT=5000
FLASK_ENV=production
```

#### Lambda Functions (Terraform Managed)
```bash
# S3 Storage
BUCKET_NAME=yoga-evaluation-bucket

# Processing Configuration
VISIBILITY_THRESHOLD=0.3
FRAME_SAMPLE_RATE=5
MAX_PROCESSING_TIME=300

# Bedrock Configuration
BEDROCK_MODEL=anthropic.claude-3-sonnet-20240229-v1:0
MAX_RETRIES=3
```

## Dependencies

### Agent Service
- `strands-agents` - AI agent framework
- `bedrock-agentcore` - AWS Bedrock integration
- `boto3>=1.34.0` - AWS SDK
- `python-dotenv>=0.19.0` - Environment configuration

### UI Service
- `flask>=3.0.0` - Web framework
- `boto3>=1.34.0` - AWS SDK
- `pycognito>=2024.5.1` - Cognito authentication
- `requests>=2.31.0` - HTTP client

### Lambda Functions
- `opencv-python` - Video processing
- `mediapipe` - Pose detection
- `numpy` - Numerical computations
- `boto3` - AWS services
- `Pillow` - Image processing

## Deployment

### Infrastructure as Code (`/terraform`)

#### Modular Terraform Architecture
```
terraform/
├── aws_base_infra/          # Main infrastructure orchestration
├── modules/                 # Reusable infrastructure modules
│   ├── cognito/            # User authentication
│   ├── ecr/                # Container registry
│   ├── ecs/                # Container orchestration
│   ├── lambda/             # Serverless functions
│   ├── s3_bucket/          # Object storage
│   └── vpc/                # Network infrastructure
├── values.tfvars           # Environment configuration
└── flag.tfvars             # Feature flags
```

#### Deploy Complete Infrastructure
```bash
# Configure deployment flags
cd terraform
# Edit flag.tfvars to enable/disable components
# Edit values.tfvars for environment-specific settings

# Deploy all infrastructure
./deploy.sh

# Or manually
cd aws_base_infra
terraform init
terraform plan -var-file="../values.tfvars" -var-file="../flag.tfvars"
terraform apply -var-file="../values.tfvars" -var-file="../flag.tfvars"
```

#### Infrastructure Components
- **Lambda Functions**: Automated deployment with S3 triggers and VPC integration
- **ECS Fargate**: Containerized service hosting with auto-scaling
- **ECR**: Container registry with lifecycle policies
- **Cognito**: User authentication and authorization
- **S3**: Video storage with encryption and lifecycle management
- **VPC**: Network isolation with public/private subnets

### Container Deployment

#### Using AgentCore CLI (Recommended)
```bash
# Configure the agent
cd services/agent
agentcore configure --entrypoint agent.py --name yoga_coach

# Launch the agent with environment variables
agentcore launch \
  --agent yoga_coach \
  --env AWS_REGION=us-east-1 \
  --env BEDROCK_MODEL=us.anthropic.claude-3-5-sonnet-20241022-v2:0 \
  --env TRAINING_LAMBDA_ARN=arn:aws:lambda:us-east-1:<account-id>:function:yoga-training-lambda \
  --env TESTING_LAMBDA_ARN=arn:aws:lambda:us-east-1:<account-id>:function:yoga-testing-lambda \
  --env S3_BUCKET=yoga-eval-bucket-1760638546
```

#### Docker Containers
- **Agent Service**: Bedrock AgentCore runtime (port 8000)
- **UI Service**: Flask web application (port 5000)

## Workflow

1. **Infrastructure Deployment**: Terraform creates all AWS resources
2. **User Registration**: Cognito-based authentication via web UI
3. **Video Upload**: Training or testing video uploaded to S3
4. **Automatic Processing**: S3 triggers invoke appropriate Lambda function
5. **AI Analysis**: MediaPipe pose detection + Bedrock validation
6. **Scoring & Feedback**: Angle-based evaluation with conversational AI guidance

## File Structure

```
/
├── services/
│   ├── agent/                     # AI Agent Service
│   │   ├── agent.py              # Main agent application
│   │   ├── tools/                # Training & evaluation tools
│   │   └── .bedrock_agentcore.yaml
│   └── ui/                       # Web Interface
│       ├── app/
│       │   ├── app.py           # Flask application
│       │   └── templates/       # HTML templates
│       └── requirements.txt
├── lambda_functions/             # Serverless Processing
│   ├── training/                # Golden standard creation
│   ├── testing/                 # Pose evaluation
│   ├── shared/                  # Common utilities
│   │   ├── yoga_pose_analyzer.py
│   │   ├── video_processor.py
│   │   └── s3_handler.py
│   └── config/                  # Pose configurations
└── terraform/                   # Infrastructure as Code
    ├── aws_base_infra/          # Main infrastructure
    ├── modules/                 # Reusable components
    │   ├── lambda/             # Lambda function module
    │   ├── cognito/            # Authentication module
    │   ├── ecs/                # Container hosting module
    │   └── ...                 # Other modules
    ├── values.tfvars           # Configuration values
    └── flag.tfvars             # Feature flags
```

## Storage Structure

```
S3 Bucket: {BUCKET_NAME}/
├── {pose-name}/
│   ├── training/
│   │   ├── videos/              # Expert training videos
│   │   ├── frames/              # Extracted frames
│   │   └── golden-standard.json # Reference measurements
│   ├── testing/
│   │   ├── videos/              # User test videos
│   │   ├── frames/              # Analysis frames
│   │   └── results/             # Evaluation results
│   └── errors/                  # Error reports and logs
```

## Performance Optimizations

- **Frame Sampling**: 5-frame validation vs full video analysis
- **Visibility Threshold**: Lowered to 0.3 for better pose detection
- **Parallel Processing**: Concurrent Lambda execution
- **ARM64 Containers**: Cost-effective ECS deployment
- **S3 Lifecycle**: Automatic cleanup of temporary files
- **Modular Infrastructure**: Independent scaling of components

## Security & Monitoring

### Security Features
- **VPC Isolation**: Lambda functions in private subnets
- **Security Groups**: Function-specific network access controls
- **IAM Roles**: Least privilege access for all services
- **S3 Encryption**: Server-side encryption at rest
- **JWT Authentication**: Secure user sessions via Cognito

### Monitoring
- **CloudWatch Logs**: Structured logging with retention policies
- **Request Tracking**: Unique request IDs for debugging
- **Performance Metrics**: Processing times and success rates
- **Infrastructure Monitoring**: Terraform-managed CloudWatch integration

## Error Handling

- **Graceful Degradation**: Fallbacks for API failures
- **User-Friendly Messages**: Clear feedback for validation failures
- **Comprehensive Logging**: Detailed error tracking across all services
- **Retry Logic**: Exponential backoff for transient failures
- **Infrastructure Resilience**: Multi-AZ deployment with auto-recovery

## API Integration

- **AWS Bedrock**: Claude 3.5 Sonnet for pose validation and feedback
- **MediaPipe**: Real-time pose detection and landmark extraction
- **S3 Events**: Automatic Lambda function triggers
- **Cognito**: JWT-based authentication and user management
