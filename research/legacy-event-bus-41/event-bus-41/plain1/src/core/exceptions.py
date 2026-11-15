class BillingError(Exception):
    def __init__(self, message: str, code: str = 'BILLING_ERROR'):
        self.message = message
        self.code = code
        super().__init__(message)

class PaymentFailedError(BillingError):
    def __init__(self, message: str, payment_id: str = None):
        self.payment_id = payment_id
        super().__init__(message, 'PAYMENT_FAILED')

class SubscriptionNotFoundError(BillingError):
    def __init__(self, subscription_id: str):
        self.subscription_id = subscription_id
        super().__init__(f'Subscription {subscription_id} not found', 'SUB_NOT_FOUND')

class IdempotencyConflictError(BillingError):
    def __init__(self, key: str):
        self.key = key
        super().__init__(f'Idempotency key {key} conflict', 'IDEMPOTENCY_CONFLICT')

class RateLimitExceededError(BillingError):
    def __init__(self, user_id: str, limit: int):
        self.user_id = user_id
        self.limit = limit
        super().__init__(f'Rate limit {limit}/min exceeded for {user_id}', 'RATE_LIMITED')

class WebhookValidationError(BillingError):
    def __init__(self, reason: str):
        super().__init__(f'Webhook validation failed: {reason}', 'WEBHOOK_INVALID')

class InsufficientPermissionsError(BillingError):
    def __init__(self, user_id: str, action: str):
        self.user_id = user_id
        self.action = action
        super().__init__(f'User {user_id} lacks permission for {action}', 'FORBIDDEN')
