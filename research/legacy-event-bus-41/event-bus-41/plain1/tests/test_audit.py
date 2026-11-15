import unittest
from src.services.audit_service import audit_service
from src.core.database import db

class TestAuditService(unittest.TestCase):
    def setUp(self):
        db.reset()

    def test_record_and_query(self):
        audit_service.record('user.login', 'usr_1', 'user', 'usr_1')
        audit_service.record('payment.done', 'usr_1', 'payment', 'pay_1')
        logs = audit_service.get_logs_for_actor('usr_1')
        self.assertEqual(len(logs), 2)

    def test_query_by_target(self):
        audit_service.record('payment.done', 'usr_1', 'payment', 'pay_1')
        logs = audit_service.get_logs_for_target('payment', 'pay_1')
        self.assertEqual(len(logs), 1)

if __name__ == '__main__':
    unittest.main()
