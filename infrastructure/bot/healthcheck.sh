#!/bin/sh
python - <<'PY'
import sys
from urllib.request import urlopen

try:
    with urlopen("http://127.0.0.1:8080/health", timeout=3) as response:
        if response.status != 200:
            raise RuntimeError(f"unexpected status: {response.status}")
except Exception:
    sys.exit(1)
PY
