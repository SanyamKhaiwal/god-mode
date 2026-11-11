from typing import Dict, Any, Optional, List
import time

class InMemoryDB:
    def __init__(self):
        self.users: Dict[str, Dict[str, Any]] = {}
        self.subscriptions: Dict[str, Dict[str, Any]] = {}
        self.invoices: Dict[str, Dict[str, Any]] = {}
        self.payments: Dict[str, Dict[str, Any]] = {}
        self.idempotency_keys: Dict[str, Dict[str, Any]] = {}
        self.api_keys: Dict[str, Dict[str, Any]] = {}
        self.usage_records: List[Dict[str, Any]] = []
        self.webhook_events: List[Dict[str, Any]] = []
        self.audit_logs: List[Dict[str, Any]] = []

    def reset(self):
        for attr in ['users', 'subscriptions', 'invoices', 'payments',
                     'idempotency_keys', 'api_keys']:
            getattr(self, attr).clear()
        for attr in ['usage_records', 'webhook_events', 'audit_logs']:
            getattr(self, attr).clear()

    def get_idempotency(self, key: str) -> Optional[Dict[str, Any]]:
        record = self.idempotency_keys.get(key)
        if record and record.get('expires_at', float('inf')) < time.time():
            del self.idempotency_keys[key]
            return None
        return record

    def save_idempotency(self, key: str, record: Dict[str, Any], ttl: int = 86400):
        record['expires_at'] = time.time() + ttl
        self.idempotency_keys[key] = record

    def get_user_subscriptions(self, user_id: str) -> List[Dict[str, Any]]:
        return [s for s in self.subscriptions.values() if s.get('user_id') == user_id]

    def get_user_invoices(self, user_id: str) -> List[Dict[str, Any]]:
        return [i for i in self.invoices.values() if i.get('user_id') == user_id]

db = InMemoryDB()
