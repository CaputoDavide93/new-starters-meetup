<p align="center">
  <img src="https://img.icons8.com/color/96/handshake.png" alt="NewStarters MeetUp Logo" width="96" height="96"/>
</p>

<h1 align="center">NewStarters MeetUp</h1>

<p align="center">
  <strong>🤝 Automated intro meeting scheduler for teams</strong>
</p>

<p align="center">
  <a href="#-features">Features</a> •
  <a href="#-quick-start">Quick Start</a> •
  <a href="#-architecture">Architecture</a> •
  <a href="#-deployment">Deployment</a> •
  <a href="#-contributing">Contributing</a>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.13+-blue.svg" alt="Python 3.13+"/>
  <img src="https://img.shields.io/badge/license-MIT-green.svg" alt="MIT License"/>
  <img src="https://img.shields.io/badge/platform-AWS%20Lambda-orange.svg" alt="AWS Lambda"/>
  <img src="https://img.shields.io/badge/arch-ARM64%20Graviton-purple.svg" alt="ARM64"/>
</p>

---

## 📖 Overview

**NewStarters MeetUp** is a Slack-integrated AWS Lambda application that automates scheduling intro meetings between new team members and existing staff. Perfect for onboarding programs, coffee chats, and buddy systems.

> 💡 **Use Case**: When a new starter joins your team, use `/newintro` in Slack to automatically schedule 1:1 meetings with team members, ensuring everyone gets a chance to connect!

---

## ✨ Features

| Feature | Description |
|---------|-------------|
| 🎯 **Slack Integration** | Easy-to-use `/newintro` slash command with modal UI |
| ☕ **Coffee Intros** | Casual meet-and-greet sessions |
| 🤝 **Buddy Intros** | Structured onboarding buddy meetings |
| 📅 **Smart Scheduling** | Finds available calendar slots (configurable time window) |
| ⚖️ **Fair Rotation** | Weighted selection ensures everyone gets a turn |
| 📆 **Business Days** | Respects weekends and configurable cadence |
| 🔄 **Azure AD Sync** | Auto-syncs team members from Azure AD groups |
| 🗑️ **Auto Cleanup** | Removes departed users automatically |
| 📊 **CloudWatch Metrics** | Built-in monitoring and observability |

---

## 🚀 Quick Start

### Prerequisites

| Requirement | Version |
|-------------|---------|
| Python | 3.13+ |
| Docker | Latest |
| AWS CLI | 2.x |
| AWS Account | With Lambda, DynamoDB, Secrets Manager |
| Slack Workspace | With admin access |
| Google Workspace | With Calendar API |
| Azure AD | With application registration |

### 1. Clone the Repository

```bash
git clone https://github.com/YOUR_USERNAME/NewStarters_MeetUp.git
cd NewStarters_MeetUp
```

### 2. Set Up Virtual Environment

```bash
python3.13 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r layer/requirements.txt
```

### 3. Configure Secrets

Create your AWS Secrets Manager secret with the required configuration (see [Configuration](#-configuration)).

### 4. Build & Deploy

```bash
# Build deployment packages
./scripts/build.sh

# Deploy to AWS (using your preferred method: SAM, CDK, Terraform, or Console)
```

---

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

### Project Structure

```
NewStarters_MeetUp/
├── 📁 src/                          # Source code
│   ├── 📁 common/                   # Shared utilities
│   │   ├── config.py                # Secrets Manager loader
│   │   ├── azure_sync.py            # Azure AD group sync
│   │   ├── calendar_utils.py        # Google Calendar ops
│   │   └── dynamo_utils.py          # DynamoDB weight mgmt
│   ├── 📁 ui_lambda/                # Slack UI handler
│   │   └── ui_entry.py
│   └── 📁 worker_lambda/            # Background worker
│       └── worker_entry.py
├── 📁 deploy/                       # Deployment packages
│   ├── 📁 ui-lambda/
│   └── 📁 worker-lambda/
├── 📁 layer/                        # Lambda Layer
│   ├── requirements.txt
│   └── 📁 python/
├── 📁 scripts/                      # Build scripts
├── 📄 LICENSE                       # MIT License
├── 📄 SECURITY.md                   # Security policy
├── 📄 CONTRIBUTING.md               # Contribution guide
└── 📄 README.md                     # This file
```

---

## ⚙️ Configuration

### AWS Secrets Manager Structure

Create a secret with the following JSON structure:

```json
{
  "slack_bot_token": "xoxb-your-bot-token",
  "slack_signing_secret": "your-signing-secret",
  "slack_trigger_channel": "C12345678",
  
  "azure_tenant_id": "your-azure-tenant-id",
  "azure_client_id": "your-azure-app-client-id",
  "azure_client_secret": "your-azure-app-secret",
  "azure_group_id": "azure-ad-group-id-for-coffee-intros",
  
  "buddy_azure_group_id": "azure-ad-group-id-for-buddy-intros",
  
  "google_service_account_key": "{\"type\":\"service_account\",...}",
  "google_delegated_user": "admin@yourdomain.com",
  "google_calendar_id": "team-calendar@group.calendar.google.com",
  
  "dynamodb_table_name": "IntroUsers",
  "buddy_dynamodb_table_name": "BuddyUsers",
  
  "meeting_title_template": "☕️ Coffee: {person1} & {person2}",
  "meeting_description_template": "Intro meeting between {person1} and {person2}",
  "buddy_meeting_title_template": "🤝 Buddy: {person1} & {person2}",
  "buddy_meeting_description_template": "Buddy intro between {person1} and {person2}"
}
```

### Environment Variables

| Variable | Lambda | Description |
|----------|--------|-------------|
| `CONFIG_SECRET` | Both | ARN of the Secrets Manager secret |
| `WORKER_FUNCTION_NAME` | UI only | Name of the worker Lambda function |

---

## 📦 Deployment

### Lambda Configuration

#### UI Lambda
| Setting | Value |
|---------|-------|
| Runtime | Python 3.13 |
| Architecture | arm64 (Graviton) |
| Handler | `ui_entry.lambda_handler` |
| Memory | 256 MB |
| Timeout | 30 seconds |

#### Worker Lambda
| Setting | Value |
|---------|-------|
| Runtime | Python 3.13 |
| Architecture | arm64 (Graviton) |
| Handler | `worker_entry.lambda_handler` |
| Memory | 512 MB |
| Timeout | 900 seconds (15 min) |

### Building the Lambda Layer

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

# Create Layer ZIP
zip -r layer-python313-arm64.zip python
```

### DynamoDB Tables

Create two tables with this schema:

| Attribute | Type | Description |
|-----------|------|-------------|
| `email` | String (PK) | User email or "members" |
| `weight` | Number | Intro count |
| `display_name` | String | User's display name |
| `member_list` | List | Active members (in "members" record) |

---

## 🔧 Slack App Setup

### 1. Create Slack App

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name: `NewStarters MeetUp`
4. Select your workspace

### 2. Configure Bot Permissions

Add these **Bot Token Scopes**:

| Scope | Purpose |
|-------|---------|
| `commands` | Handle slash commands |
| `chat:write` | Post messages |

### 3. Create Slash Command

| Setting | Value |
|---------|-------|
| Command | `/newintro` |
| Request URL | `https://your-api-gateway-url/slack/events` |
| Description | Schedule intro meetings |

### 4. Install to Workspace

Click **Install to Workspace** and authorize.

---

## 📊 Usage

### The `/newintro` Command

1. Type `/newintro` in any Slack channel
2. A modal appears with options:

   | Field | Description |
   |-------|-------------|
   | **Type** | ☕ Coffee or 🤝 Buddy |
   | **Emails** | New starter email(s), comma-separated |
   | **Start Date** | When to start scheduling |
   | **Count** | Number of meetings per person |

3. Click **Book** and watch the magic! ✨

### Example Output

```
☕ Booking Coffee…
✅ John Doe ↔ Jane Smith — 15 Jan 11:00
✅ John Doe ↔ Bob Wilson — 17 Jan 14:30
✅ John Doe ↔ Alice Brown — 21 Jan 11:15
✅ Booking complete! 3 succeeded, 0 failed.
```

---

## 🔒 Security

This project takes security seriously. See [SECURITY.md](SECURITY.md) for:

- 🔐 How to report vulnerabilities
- 🛡️ Security best practices
- ✅ Deployment security checklist

**Key Security Features:**
- All secrets stored in AWS Secrets Manager (not env vars)
- Slack request signature verification
- IAM least privilege principle
- No hardcoded credentials

---

## 🧪 Local Development

### Running Locally

```bash
# Activate virtual environment
source venv/bin/activate

# Set local environment
export CONFIG_SECRET="local"  # Uses local config
export WORKER_FUNCTION_NAME="intro-worker"

# Run tests
pytest
```

### Testing Imports (Lambda Environment Simulation)

```bash
docker run --rm \
  --platform linux/arm64 \
  --entrypoint "" \
  -v "$(pwd)/layer/python:/opt/python" \
  public.ecr.aws/lambda/python:3.13 \
  python -c "
import sys
sys.path.insert(0, '/opt/python')
from intro_common.calendar_utils import get_calendar_service
print('✅ Imports work!')
"
```

---

## 📈 Monitoring

### CloudWatch Metrics

| Metric | Description |
|--------|-------------|
| `IntroBookings/SuccessCount` | Successful bookings |
| `IntroBookings/FailureCount` | Failed bookings |
| `IntroBookings/Duration` | Booking process time |

### CloudWatch Logs

```bash
# UI Lambda logs
aws logs tail /aws/lambda/intro-ui-lambda --follow

# Worker Lambda logs
aws logs tail /aws/lambda/intro-worker-lambda --follow
```

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| "No partner available" | Check Azure AD group sync and DynamoDB table |
| "Calendar slot not found" | Verify Google Calendar permissions |
| "Timeout" | Increase Lambda memory/timeout, reduce meeting count |
| "Signature mismatch" | Verify Slack signing secret |
| "Permission denied" | Check IAM roles and policies |

---

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for:

- 📜 Code of conduct
- 💻 Development setup
- 📏 Coding standards
- 📤 Pull request process

---

## 📦 Dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| `slack-sdk` | 3.39.0 | Slack API client |
| `slack-bolt` | 1.27.0 | Slack app framework |
| `google-api-python-client` | 2.187.0 | Google Calendar API |
| `google-auth` | 2.45.0 | Google authentication |
| `azure-identity` | 1.25.1 | Azure AD authentication |
| `msal` | 1.34.0 | Microsoft authentication |
| `boto3` | 1.42.19 | AWS SDK |
| `pytz` | 2025.2 | Timezone handling |

---

## 📄 License

This project is licensed under the **MIT License** - see the [LICENSE](LICENSE) file for details.

---

## 👤 Author

**Davide Caputo**

- 📧 Email: [CaputoDav93@Gmail.com](mailto:CaputoDav93@Gmail.com)
- 🐙 GitHub: [@CaputoDavide93](https://github.com/CaputoDavide93)

---

## 🙏 Acknowledgments

- [Slack Bolt](https://slack.dev/bolt-python/) - Excellent Slack framework
- [Google APIs](https://developers.google.com/calendar) - Calendar integration
- [Azure Identity](https://docs.microsoft.com/en-us/azure/active-directory/) - AD sync

---

<p align="center">
  Made with ❤️ for better team connections
</p>
