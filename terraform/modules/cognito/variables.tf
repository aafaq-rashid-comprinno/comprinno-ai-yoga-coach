variable "user_pool_name" {
  description = "Name of the Cognito User Pool"
  type        = string
}

variable "password_policy_min_length" {
  description = "Minimum length of the password"
  type        = number
  default     = 8
}

variable "password_policy_require_upper" {
  description = "Whether to require uppercase characters"
  type        = bool
  default     = true
}

variable "password_policy_require_lower" {
  description = "Whether to require lowercase characters"
  type        = bool
  default     = true
}

variable "password_policy_require_numbers" {
  description = "Whether to require numbers"
  type        = bool
  default     = true
}

variable "password_policy_require_symbols" {
  description = "Whether to require symbols"
  type        = bool
  default     = false
}

variable "mfa_configuration" {
  description = "MFA configuration"
  type        = string
  default     = "OFF"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default     = {}
}
