variable "storage_bucket_name" {
  description = "Name of the S3 storage bucket"
  type        = string
}

variable "versioning_enabled" {
  description = "Whether to enable versioning"
  type        = bool
  default     = true
}

variable "lifecycle_enabled" {
  description = "Whether to enable lifecycle policies"
  type        = bool
  default     = true
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
