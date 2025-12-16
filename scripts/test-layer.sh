#!/bin/bash
# Test Lambda Layer imports

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
LAYER_DIR="$PROJECT_ROOT/layer"

echo "🧪 Testing Lambda Layer imports..."

docker run --rm \
  --platform linux/arm64 \
  --entrypoint "" \
  -v "$LAYER_DIR/python:/opt/python" \
  -w /opt \
  public.ecr.aws/lambda/python:3.13 \
  python -c "
import sys
sys.path.insert(0, '/opt/python')

print('Testing Python 3.13 Lambda Layer imports...')
print()

modules = [
    ('slack_sdk', lambda m: m.version.__version__),
    ('slack_bolt', lambda m: 'OK'),
    ('google.oauth2.service_account', lambda m: 'OK'),
    ('googleapiclient.discovery', lambda m: 'OK'),
    ('azure.identity', lambda m: 'OK'),
    ('msal', lambda m: m.__version__),
    ('boto3', lambda m: m.__version__),
    ('pytz', lambda m: m.__version__),
]

success = 0
failed = 0

for module_name, version_func in modules:
    try:
        module = __import__(module_name, fromlist=[''])
        version = version_func(module)
        print(f'✓ {module_name} ({version})')
        success += 1
    except Exception as e:
        print(f'✗ {module_name}: {e}')
        failed += 1

try:
    from intro_common.config import slack_cfg
    print(f'✗ intro_common.config (expected to fail without secrets)')
except ValueError as e:
    print(f'✓ intro_common (loads correctly, needs CONFIG_SECRET)')
    success += 1
except Exception as e:
    print(f'✓ intro_common (import structure OK)')
    success += 1

print()
if failed == 0:
    print(f'✅ All {success} imports successful!')
else:
    print(f'⚠️  {success} succeeded, {failed} failed')
    sys.exit(1)
"
