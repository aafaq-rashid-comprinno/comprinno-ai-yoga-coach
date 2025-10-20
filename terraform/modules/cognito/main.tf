resource "aws_cognito_user_pool" "main" {
  name = var.user_pool_name

  password_policy {
    minimum_length    = var.password_policy_min_length
    require_uppercase = var.password_policy_require_upper
    require_lowercase = var.password_policy_require_lower
    require_numbers   = var.password_policy_require_numbers
    require_symbols   = var.password_policy_require_symbols
  }

  mfa_configuration = var.mfa_configuration

  tags = var.tags
}

resource "aws_cognito_user_pool_client" "main" {
  name         = "${var.user_pool_name}-client"
  user_pool_id = aws_cognito_user_pool.main.id

  generate_secret = false

  explicit_auth_flows = [
    "ADMIN_NO_SRP_AUTH",
    "USER_PASSWORD_AUTH"
  ]
}
