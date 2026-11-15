#!/usr/bin/env bash
# usage: check.sh <run dir>  -> original 23 tests (restored unmodified) + structural checks
d="$1"; H="$(dirname "$0")/hidden_tests"
mkdir -p "$d/.hidden"; cp "$H"/*.py "$d/.hidden/"
r=$(cd "$d" && python -m pytest -q .hidden -p no:cacheprovider 2>&1 | tail -1)
rm -r "$d/.hidden"
imp=$(grep -lE "audit_service" "$d/src/services/billing_service.py" "$d/src/services/subscription_service.py" "$d/src/services/webhook_service.py" 2>/dev/null | wc -l)
wimp=$(grep -cE "import (billing|subscription)_service|from src.services.(billing|subscription)_service" "$d/src/services/webhook_service.py")
bus=$([ -f "$d/src/core/events.py" ] && echo yes || echo no)
own=$(cd "$d" && python -m pytest -q -p no:cacheprovider 2>&1 | tail -1)
echo "original-tests: $r | own-suite: $own | events.py: $bus | services-still-using-audit: $imp | webhook-direct-imports: $wimp"
