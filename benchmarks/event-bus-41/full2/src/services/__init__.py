# Import the event-subscribing services so their handlers are registered on
# the event bus no matter which service a caller imports first.
from src.services import audit_service, billing_service, subscription_service  # noqa: F401
