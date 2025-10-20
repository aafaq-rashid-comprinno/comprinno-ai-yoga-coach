output "storage_bucket_name" {
  description = "Name of the S3 storage bucket"
  value       = aws_s3_bucket.storage.bucket
}

output "storage_bucket_arn" {
  description = "ARN of the S3 storage bucket"
  value       = aws_s3_bucket.storage.arn
}

output "storage_bucket_domain_name" {
  description = "Domain name of the S3 storage bucket"
  value       = aws_s3_bucket.storage.bucket_domain_name
}
