"""Billing shape tests: monthly checkout carries the 14-day trial; /pricing notes it."""

import pathlib
import tempfile
import unittest
import urllib.request

from dataset_ancestry import web


class BillingTests(unittest.TestCase):
    def test_monthly_checkout_carries_14_day_trial(self):
        env = {
            "STRIPE_SECRET_KEY": "sk_test_x",
            "STRIPE_WEBHOOK_SECRET": "whsec_test",
            "STRIPE_PRICES": "team=price_1,business=price_2,enterprise=price_3",
            "PUBLIC_URL": "https://example.test",
        }
        with tempfile.TemporaryDirectory() as t:
            srv = web.make_server("127.0.0.1", 0, pathlib.Path(t), env=env)
            try:
                billing = srv.RequestHandlerClass.billing
                sent = {}
                billing._stripe = lambda path, form: sent.update(form) or {"url": "https://checkout.test/s"}
                self.assertEqual(billing.checkout("team"), "https://checkout.test/s")
                self.assertEqual(sent["mode"], "subscription")
                self.assertEqual(sent["subscription_data[trial_period_days]"], "14")
                self.assertEqual(sent["line_items[0][price]"], "price_1")
            finally:
                srv.server_close()

    def test_pricing_page_notes_trial_when_billing_enabled(self):
        env = {
            "STRIPE_SECRET_KEY": "sk_test_x",
            "STRIPE_WEBHOOK_SECRET": "whsec_test",
            "STRIPE_PRICES": "team=price_1",
            "PUBLIC_URL": "https://example.test",
        }
        with tempfile.TemporaryDirectory() as t:
            srv = web.make_server("127.0.0.1", 0, pathlib.Path(t), env=env)
            try:
                import threading

                threading.Thread(target=srv.serve_forever, daemon=True).start()
                base = f"http://127.0.0.1:{srv.server_address[1]}"
                page = urllib.request.urlopen(base + "/pricing", timeout=30).read()
                self.assertIn(b"14-day free trial", page)
                self.assertIn(b"Subscribe", page)
            finally:
                srv.shutdown()
                srv.server_close()


if __name__ == "__main__":
    unittest.main()
