import unittest
import json
import hmac
import hashlib
from src.services.webhook_service import webhook_service
from src.core.config import settings
from src.core.database import db
from src.core.telemetry import telemetry

class TestWebhookService(unittest.TestCase):
    def setUp(self):
        db.reset()
        telemetry.reset()

    def _make_signed_payload(self, data):
        body = json.dumps(data).encode()
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        return body, sig

    def test_valid_webhook(self):
        body, sig = self._make_signed_payload({'id': 'evt_1', 'type': 'invoice.payment_succeeded'})
        result = webhook_service.process_webhook(body, sig)
        self.assertEqual(result['status'], 'processed')

    def test_duplicate_webhook(self):
        body, sig = self._make_signed_payload({'id': 'evt_2', 'type': 'invoice.payment_succeeded'})
        webhook_service.process_webhook(body, sig)
        result = webhook_service.process_webhook(body, sig)
        self.assertEqual(result['status'], 'ignored_duplicate')

    def test_invalid_signature(self):
        body = b'{"id": "evt_3", "type": "test"}'
        result = webhook_service.process_webhook(body, 'bad_sig')
        self.assertEqual(result['status'], 'error')

    def test_malformed_json(self):
        body = b'not json at all'
        sig = hmac.new(settings.WEBHOOK_SECRET.encode(), body, hashlib.sha256).hexdigest()
        result = webhook_service.process_webhook(body, sig)
        self.assertEqual(result['status'], 'error')

if __name__ == '__main__':
    unittest.main()
