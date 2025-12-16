# NewStarters MeetUp 🤝

A Slack-integrated AWS Lambda application for scheduling intro meetings between new starters and existing team members. Built for automated coffee chats and buddy introductions.

## 🎯 Features

- **Slack Modal Interface** - Easy-to-use `/newintro` slash command with a modal form
- **Two Meeting Types**:
  - ☕️ **Coffee Intros** - Casual meet-and-greet sessions
  - 🤝 **Buddy Intros** - Structured onboarding buddy meetings
- **Smart Scheduling** - Automatically finds available calendar slots
- **Azure AD Integration** - Syncs team members from Azure AD groups
- **Weighted Selection** - Prioritizes team members with fewer intros
- **Google Calendar Integration** - Creates calendar events with invites

## 📁 Project Structure

```
NewStarters_MeetUp/
├── src/                          # Source code
│   ├── ui_lambda/                # Slack UI Lambda function
│   │   ├── __init__.py
│   │   └── handler.py            # Slash command & modal handler
│   ├── worker_lambda/            # Background worker Lambda
│   │   ├── __init__.py
│   │   └── handler.py            # Booking logic & calendar integration
│   └── common/                   # Shared utilities (development copy)
│       ├── __init__.py
│       ├── config.py             # Configuration from Secrets Manager
│       ├── azure_sync.py         # Azure AD group sync
│       ├── calendar_utils.py     # Google Calendar operations
│       └── dynamo_utils.py       # DynamoDB weight management
├── layer/                        # Lambda Layer (Python 3.13 ARM64)
│   ├── requirements.txt          # Layer dependencies
│   └── python/                   # Installed packages
│       ├── intro_common/         # Shared code (deployed version)
│       ├── slack_sdk/
│       ├── slack_bolt/
│       ├── google-api-python-client/
│       ├── azure-identity/
│       └── ...
├── .gitignore
└── README.md
```

## 🏗️ Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Slack User    │────▶│  API Gateway     │────▶│  UI Lambda      │
│  /newintro cmd  │     │  (HTTP Endpoint) │     │  (Modal Handler)│
└─────────────────┘     └──────────────────┘     └────────┬────────┘
                                                          │
                                                          │ Async Invoke
                                                          ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│  Google         │◀────│  Worker Lambda   │────▶│  DynamoDB       │
│  Calendar       │     │  (Booking Logic) │     │  (Weights)      │
└─────────────────┘     └────────┬─────────┘     └─────────────────┘
                                 │
                                 ▼
                        ┌──────────────────┐
                        │  Azure AD        │
                        │  (Group Members) │
                        └──────────────────┘
```

## 🚀 Deployment

### Prerequisites

- AWS Account with Lambda, DynamoDB, Secrets Manager access
- Slack App with slash commands enabled
- Google Workspace with Calendar API access
- Azure AD with application registration
- Docker (for building the Layer)

### 1. Configure AWS Secrets Manager

Create a secret with the following JSON structure:

```json
{
  "slack_bot_token": "xoxb-...",
  "slack_signing_secret": "...",
  "slack_trigger_channel": "C12345678",
  
  "azure_tenant_id": "...",
  "azure_client_id": "...",
  "azure_client_secret": "...",
  "azure_group_id": "...",
  
  "buddy_azure_group_id": "...",
  
  "google_service_account_key": "{...}",
  "google_delegated_user": "admin@company.com",
  "google_calendar_id": "company-calendar@group.calendar.google.com",
  
  "dynamodb_table_name": "intro-weights",
  "buddy_dynamodb_table_name": "buddy-intro-weights",
  
  "meeting_title_template": "☕️ Coffee: {person1} & {person2}",
  "meeting_description_template": "Intro meeting between {person1} and {person2}",
  "buddy_meeting_title_template": "🤝 Buddy: {person1} & {person2}",
  "buddy_meeting_description_template": "Buddy meeting between {person1} and {person2}"
}
```

### 2. Build the Lambda Layer

```bash
cd layer

# Build for Python 3.13 ARM64 (Graviton)
docker run --rm \
  --platform linux/arm64 \
  --entrypoint "" \
  -v "$(pwd):/layer" \
  -w /layer \
  public.ecr.aws/lambda/python:3.13 \
  pip install -t /layer/python -r requirements.txt --no-cache-dir

# Create the Layer ZIP
zip -r layer-python313-arm64.zip python
```

### 3. Deploy Lambda Functions

#### UI Lambda
- **Runtime**: Python 3.13
- **Architecture**: arm64
- **Handler**: `handler.lambda_handler`
- **Memory**: 256 MB
- **Timeout**: 30 seconds
- **Environment Variables**:
  - `CONFIG_SECRET`: ARN of the Secrets Manager secret
  - `WORKER_FUNCTION_NAME`: Name of the worker Lambda

#### Worker Lambda
- **Runtime**: Python 3.13
- **Architecture**: arm64
- **Handler**: `handler.lambda_handler`
- **Memory**: 512 MB
- **Timeout**: 15 minutes (900 seconds)
- **Environment Variables**:
  - `CONFIG_SECRET`: ARN of the Secrets Manager secret

### 4. Configure Slack App

1. Create a Slack App at https://api.slack.com/apps
2. Add the following Bot Token Scopes:
   - `commands`
   - `chat:write`
3. Create a Slash Command:
   - **Command**: `/newintro`
   - **Request URL**: Your API Gateway URL
4. Install the app to your workspace

### 5. Create DynamoDB Tables

Create two tables with the following schema:

| Table Name | Partition Key | Attributes |
|------------|---------------|------------|
| `intro-weights` | `email` (String) | `weight` (Number), `member_list` (List) |
| `buddy-intro-weights` | `email` (String) | `weight` (Number), `member_list` (List) |

## 🔧 Local Development

### Setup

```bash
# Clone the repository
git clone https://github.com/CaputoDavide93/NewStarters_MeetUp.git
cd NewStarters_MeetUp

# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r layer/requirements.txt
```

### Testing Imports

```bash
# Test with Docker (simulates Lambda environment)
docker run --rm \
  --platform linux/arm64 \
  --entrypoint "" \
  -v "$(pwd)/layer/python:/opt/python" \
  public.ecr.aws/lambda/python:3.13 \
  python -c "
import sys
sys.path.insert(0, '/opt/python')
from intro_common.config import slack_cfg
print('✓ Imports work!')
"
```

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `slack-sdk` | 3.39.0 | Slack API client |
| `slack-bolt` | 1.27.0 | Slack app framework |
| `google-api-python-client` | 2.187.0 | Google Calendar API |
| `google-auth` | 2.43.0 | Google authentication |
| `azure-identity` | 1.25.1 | Azure AD authentication |
| `msal` | 1.34.0 | Microsoft authentication |
| `boto3` | 1.42.9 | AWS SDK |
| `cryptography` | 46.0.3 | Cryptographic operations |
| `pytz` | 2025.2 | Timezone handling |

## 🔒 Security

- All secrets stored in AWS Secrets Manager
- Lambda functions use IAM roles with least privilege
- Slack request signature verification enabled
- Google Calendar uses delegated service account

## 📊 CloudWatch Metrics

The worker Lambda publishes custom metrics:

- `IntroBookings/SuccessCount` - Successful bookings
- `IntroBookings/FailureCount` - Failed bookings
- `IntroBookings/Duration` - Booking process duration

## 🐛 Troubleshooting

### Common Issues

1. **"No partner available"** - Check Azure AD group sync and DynamoDB table
2. **"Calendar slot not found"** - Verify Google Calendar permissions and delegated user
3. **"Timeout"** - Increase Lambda memory/timeout, reduce number of meetings

### Logs

```bash
# View UI Lambda logs
aws logs tail /aws/lambda/intro-ui-lambda --follow

# View Worker Lambda logs
aws logs tail /aws/lambda/intro-worker-lambda --follow
```

## 📝 License

Internal use only.

## 👥 Contributors

- Davide Caputo ([@CaputoDavide93](https://github.com/CaputoDavide93))
