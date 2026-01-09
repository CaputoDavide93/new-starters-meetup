# 🔐 Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.x.x   | :white_check_mark: |

## 🚨 Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please report it responsibly.

### How to Report

1. **DO NOT** open a public GitHub issue for security vulnerabilities
2. Email the maintainer directly at: **CaputoDav93@Gmail.com**
3. Include as much detail as possible:
   - Description of the vulnerability
   - Steps to reproduce
   - Potential impact
   - Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours of your report
- **Status Update**: Within 7 days with an assessment
- **Resolution**: Security patches are prioritized and released ASAP

### Scope

This policy applies to:
- The core application code (`src/`, `deploy/`)
- Configuration handling
- API integrations (Slack, Azure AD, Google Calendar)
- AWS infrastructure patterns

## 🛡️ Security Best Practices

When deploying this application, ensure you follow these security practices:

### Secrets Management

- ✅ **DO** store all secrets in AWS Secrets Manager
- ✅ **DO** use IAM roles with least privilege
- ✅ **DO** rotate secrets regularly
- ❌ **DON'T** commit secrets to version control
- ❌ **DON'T** hardcode credentials in code
- ❌ **DON'T** log sensitive information

### Required Secrets (Store in AWS Secrets Manager)

```json
{
  "slack_bot_token": "xoxb-...",
  "slack_signing_secret": "...",
  "azure_tenant_id": "...",
  "azure_client_id": "...",
  "azure_client_secret": "...",
  "google_service_account_key": "{...}",
  "...": "..."
}
```

### AWS IAM Permissions

The Lambda functions require minimal permissions:

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:SECRET_NAME"
    },
    {
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:PutItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Scan",
        "dynamodb:BatchGetItem"
      ],
      "Resource": "arn:aws:dynamodb:REGION:ACCOUNT:table/TABLE_NAME"
    },
    {
      "Effect": "Allow",
      "Action": [
        "lambda:InvokeFunction"
      ],
      "Resource": "arn:aws:lambda:REGION:ACCOUNT:function:WORKER_FUNCTION"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cloudwatch:PutMetricData"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:REGION:ACCOUNT:*"
    }
  ]
}
```

### Network Security

- Deploy Lambda functions in a VPC if accessing internal resources
- Use VPC endpoints for AWS services
- Configure security groups appropriately

### Slack Security

- Verify request signatures (handled by `slack-bolt`)
- Use HTTPS for all endpoints
- Limit slash command access to specific channels if needed

### Azure AD Security

- Use application (client) credentials, not user credentials
- Grant minimal Microsoft Graph permissions:
  - `GroupMember.Read.All` (for group member sync)
- Consider using managed identities where possible

### Google Workspace Security

- Use service account with domain-wide delegation
- Limit Calendar API scopes to what's needed
- Rotate service account keys periodically

## 📋 Security Checklist for Deployment

Before deploying to production:

- [ ] All secrets stored in AWS Secrets Manager (not environment variables)
- [ ] Lambda IAM roles follow least privilege principle
- [ ] Slack request signature verification is enabled
- [ ] API Gateway has appropriate throttling configured
- [ ] CloudWatch Logs do not contain sensitive data
- [ ] DynamoDB tables have encryption at rest enabled
- [ ] No hardcoded credentials in codebase
- [ ] `.gitignore` excludes all sensitive files
- [ ] Regular dependency updates for security patches

## 🔄 Dependency Security

We recommend:

1. Regular dependency audits: `pip audit`
2. Dependabot or similar for automated updates
3. Pin dependency versions in `requirements.txt`
4. Review changelogs before updating major versions

## 📝 Changelog

| Date | Description |
|------|-------------|
| 2026-01-09 | Initial security policy |

---

Thank you for helping keep this project secure! 🙏
