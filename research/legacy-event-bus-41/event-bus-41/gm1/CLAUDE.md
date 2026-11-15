## Learnings

- Event-bus subscribers register at import time; `src/services/__init__.py` imports audit/billing/subscription services so their handlers exist whenever any service is imported.
