variable "function_name" {
  description = "Name of the Lambda function"
  type        = string
}

variable "runtime" {
  description = "Runtime for the Lambda function"
  type        = string
  default     = "python3.11"
}

variable "handler" {
  description = "Function entrypoint in your code"
  type        = string
}

variable "source_path" {
  description = "Path to the source code directory"
  type        = string
}

variable "timeout" {
  description = "Amount of time your Lambda Function has to run in seconds"
  type        = number
  default     = 300
}

variable "memory_size" {
  description = "Amount of memory in MB your Lambda Function can use at runtime"
  type        = number
  default     = 512
}

variable "environment_variables" {
  description = "Map of environment variables"
  type        = map(string)
  default     = {}
}

variable "s3_bucket" {
  description = "S3 bucket name for Lambda triggers"
  type        = string
}

variable "s3_trigger_prefix" {
  description = "S3 object key prefix for triggering Lambda"
  type        = string
  default     = ""
}

variable "s3_trigger_suffix" {
  description = "S3 object key suffix for triggering Lambda"
  type        = string
  default     = ""
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}

variable "vpc_config" {
  description = "VPC configuration for Lambda function"
  type = object({
    subnet_ids = list(string)
  })
  default = null
}

variable "vpc_id" {
  description = "VPC ID for security group creation"
  type        = string
  default     = null
}

variable "layers" {
  description = "List of Lambda Layer Version ARNs to attach to function"
  type        = list(string)
  default     = []
}
