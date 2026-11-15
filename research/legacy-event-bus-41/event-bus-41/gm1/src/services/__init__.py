# Import subscribers so their event-bus handlers are registered whenever any
# service module is imported.
from src.services import audit_service, billing_service, subscription_service  # noqa: F401
