
## Learnings
- Services communicate via `src.core.events.event_bus`; subscribers are wired in `src/services/__init__.py` (`register_event_handlers`). Do not import audit/billing/subscription services across services.
