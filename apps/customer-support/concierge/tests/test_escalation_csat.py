"""
test_escalation_csat.py — Diagnostic test suite verifying escalation and CSAT
workflows, verified recipient routing (NO-OPEN-RELAY-V1), and UI integration (Issue #21).
"""

import unittest
from pathlib import Path

from _test_lib import load_app_js


class ConciergeEscalationAndCsatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app_js, err = load_app_js()
        if err:
            raise RuntimeError(err)
        cls.app_js_path = Path(__file__).resolve().parent.parent / "ui" / "app.js"
        cls.setup_py_path = Path(__file__).resolve().parent.parent / "setup.py"
        cls.setup_text = cls.setup_py_path.read_text(encoding="utf-8")

    def test_setup_py_ticket_escalation_workflow(self):
        """ticket_escalation must route alert strictly to the team's Slack channel (#support)."""
        self.assertIn('"workflow_id": "ticket_escalation"', self.setup_text)
        start = self.setup_text.find('"workflow_id": "ticket_escalation"')
        end = self.setup_text.find('"workflow_id": "csat_request"', start)
        block = self.setup_text[start:end]

        # Slack message to team is preserved as fixed recipient
        self.assertIn('"channel": "#support"', block)
        self.assertIn('"service": "slack"', block)
        # Email step omitted pending platform fix for customer routing
        self.assertNotIn('"service": "email"', block)

    def test_setup_py_csat_request_workflow_present(self):
        """csat_request workflow definition exists in setup.py."""
        self.assertIn('"workflow_id": "csat_request"', self.setup_text)

    def test_setup_py_event_bindings_no_open_relay(self):
        """EVENT_BINDINGS must map customer_email to user.email, not unverified free text."""
        start = self.setup_text.find("EVENT_BINDINGS")
        block = self.setup_text[start:start + 400]
        self.assertIn('"customer_email": "user.email"', block)

    def test_app_js_defines_run_saga(self):
        """ui/app.js must define the standard SAGA-GUARD-V1 runSaga helper."""
        self.assertIn("function runSaga(workflowId, input)", self.app_js)
        self.assertIn("services.workflow.run", self.app_js)

    def test_app_js_escalate_handler(self):
        """ui/app.js must define escalateTicket invoking ticket_escalation with runSaga."""
        self.assertIn("function escalateTicket", self.app_js)
        self.assertIn("'ticket_escalation'", self.app_js)
        self.assertIn("runSaga('ticket_escalation'", self.app_js)

    def test_app_js_ui_actions(self):
        """ui/app.js must render Escalate button for open tickets and Resolve action."""
        self.assertIn("Escalate", self.app_js)
        self.assertIn("Resolve", self.app_js)


if __name__ == "__main__":
    unittest.main()
