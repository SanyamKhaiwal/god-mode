# Wire event subscribers onto the shared bus. Importing any service module
# imports this package first, so subscriptions exist before anything publishes.
from src.services.audit_service import audit_service
from src.services.billing_service import billing_service
from src.services.subscription_service import subscription_service


def register_event_handlers():
    # Safe to call repeatedly: EventBus.subscribe ignores duplicate handlers
    audit_service.register_event_handlers()
    billing_service.register_event_handlers()
    subscription_service.register_event_handlers()


register_event_handlers()
