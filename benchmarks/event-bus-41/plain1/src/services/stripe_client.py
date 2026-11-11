import time
from typing import Dict, Any, Optional

class MockStripeClient:
    def __init__(self):
        self._customers: Dict[str, Dict[str, Any]] = {}
        self._subscriptions: Dict[str, Dict[str, Any]] = {}

    def create_customer(self, email: str, name: str = '') -> Dict[str, Any]:
        cid = f'cus_{int(time.time()*1000)}'
        customer = {'id': cid, 'email': email, 'name': name}
        self._customers[cid] = customer
        return customer

    def create_checkout_session(self, customer_id: str, plan_tier: str,
                                 success_url: str = '', cancel_url: str = '') -> Dict[str, Any]:
        return {
            'id': f'cs_test_{int(time.time()*1000)}',
            'url': f'https://checkout.stripe.com/pay/{plan_tier}',
            'customer': customer_id
        }

    def create_subscription(self, customer_id: str, price_id: str) -> Dict[str, Any]:
        sid = f'sub_stripe_{int(time.time()*1000)}'
        sub = {'id': sid, 'customer': customer_id, 'status': 'active',
               'current_period_end': int(time.time()) + 30*86400}
        self._subscriptions[sid] = sub
        return sub

    def cancel_subscription(self, sub_id: str, immediate: bool = False) -> Dict[str, Any]:
        return {'id': sub_id, 'status': 'canceled' if immediate else 'active',
                'cancel_at_period_end': not immediate}

    def create_payment_intent(self, amount: int, currency: str,
                               customer_id: str = None, idempotency_key: str = None) -> Dict[str, Any]:
        return {'id': f'pi_{int(time.time()*1000)}', 'amount': amount,
                'currency': currency, 'status': 'succeeded'}

    def refund_payment(self, payment_intent_id: str, amount: int = None) -> Dict[str, Any]:
        return {'id': f'rf_{int(time.time()*1000)}', 'payment_intent': payment_intent_id,
                'status': 'succeeded', 'amount': amount}

stripe_client = MockStripeClient()
