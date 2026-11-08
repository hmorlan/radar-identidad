"""Tests de la alerta de fuentes caídas (sin red)."""
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

import check_feeds  # noqa: E402
import source_health_alert as alert  # noqa: E402


def r(source, verdict, group="noticias", error="", pending=False, newest="2026-11-01"):
    return {"group": group, "source": source, "verdict": verdict, "status": 200,
            "entries": 3, "newest": newest, "error": error, "pending": pending}


class EvaluateTest(unittest.TestCase):
    def test_single_failure_does_not_alert(self):
        state, alerting, _ = alert.evaluate([r("a", "FALLA", error="timeout")], {}, 2, "2026-11-07")
        self.assertEqual(alerting, [])
        self.assertEqual(state["streaks"]["noticias|a"]["count"], 1)

    def test_second_consecutive_failure_alerts(self):
        state, _, _ = alert.evaluate([r("a", "FALLA")], {}, 2, "2026-11-06")
        state, alerting, _ = alert.evaluate([r("a", "FALLA")], state, 2, "2026-11-07")
        self.assertEqual([a["source"] for a in alerting], ["a"])
        self.assertEqual(alerting[0]["since"], "2026-11-06")
        self.assertEqual(state["alerted"], ["noticias|a"])

    def test_recovery_resets_streak(self):
        state, _, _ = alert.evaluate([r("a", "FALLA")], {}, 2, "2026-11-06")
        state, alerting, _ = alert.evaluate([r("a", "OK")], state, 2, "2026-11-07")
        self.assertEqual(alerting, [])
        self.assertEqual(state["streaks"], {})
        state, alerting, _ = alert.evaluate([r("a", "FALLA")], state, 2, "2026-11-08")
        self.assertEqual(alerting, [])

    def test_inactive_is_informational_and_pending_ignored(self):
        _, alerting, info = alert.evaluate(
            [r("quieta", "INACTIVA"), r("nueva", "FALLA", pending=True)], {}, 1, "2026-11-07")
        self.assertEqual(alerting, [])
        self.assertEqual([i["source"] for i in info], ["quieta"])

    def test_issue_body_mentions_owner_and_lists_sources(self):
        _, alerting, info = alert.evaluate([r("CNBV · página", "FALLA", group="reguladores",
                                              error="la página | cambió")], {}, 1, "2026-11-07")
        body = alert.render_issue(alerting, info, "2026-11-07")
        self.assertIn("@hmorlan", body)
        self.assertIn("CNBV · página", body)
        self.assertNotIn("la página | cambió", body)  # el | rompería la tabla


class SyncIssueTest(unittest.TestCase):
    def _run(self, open_number, alerting, prev, now):
        calls = []

        def fake_gh(*args):
            calls.append(args)
            return ""

        with mock.patch.object(alert, "gh", side_effect=fake_gh), \
             mock.patch.object(alert, "open_issue_number", return_value=open_number), \
             mock.patch.object(alert.subprocess, "run"):
            action = alert.sync_issue("o/r", alerting, [], prev, now, "2026-11-07")
        return action, [c[0] + " " + c[1] for c in calls]

    def test_opens_issue(self):
        action, calls = self._run(None, [{"group": "g", "source": "s", "since": "d", "streak": 2}], [], ["g|s"])
        self.assertEqual(action, "abierto")
        self.assertEqual(calls, ["issue create"])

    def test_updates_quietly_when_set_unchanged(self):
        action, calls = self._run(5, [{"group": "g", "source": "s", "since": "d", "streak": 3}], ["g|s"], ["g|s"])
        self.assertEqual(action, "actualizado")
        self.assertEqual(calls, ["issue edit"])

    def test_closes_when_recovered(self):
        action, calls = self._run(5, [], ["g|s"], [])
        self.assertEqual(action, "cerrado")
        self.assertEqual(calls, ["issue comment", "issue close"])

    def test_nothing_to_do(self):
        action, calls = self._run(None, [], [], [])
        self.assertEqual((action, calls), ("sin cambios", []))


class MainTest(unittest.TestCase):
    def _main(self, results, issues, tmp):
        import json, os, tempfile
        res = Path(tmp) / "r.json"
        res.write_text(json.dumps(results))
        state = Path(tmp) / "s.json"
        argv = ["x", "--results", str(res), "--state", str(state), "--min-streak", "1"]
        with mock.patch.object(sys, "argv", argv), \
             mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "o/r", "GITHUB_STEP_SUMMARY": ""}), \
             mock.patch.object(alert, "issues_enabled", return_value=issues), \
             mock.patch.object(alert, "sync_issue", return_value="abierto") as sync:
            code = alert.main()
        return code, sync.called, json.loads(state.read_text())

    def test_alert_without_issues_fails_the_run_and_keeps_state(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, synced, state = self._main([r("a", "FALLA")], False, tmp)
        self.assertEqual(code, 1)
        self.assertFalse(synced)
        self.assertEqual(state["alerted"], ["noticias|a"])

    def test_healthy_run_passes(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            code, synced, _ = self._main([r("a", "OK")], True, tmp)
        self.assertEqual(code, 0)
        self.assertTrue(synced)

    def test_github_error_does_not_crash(self):
        import tempfile
        with tempfile.TemporaryDirectory() as tmp, \
             mock.patch.object(alert, "gh", side_effect=RuntimeError("403")):
            res = Path(tmp) / "r.json"
            res.write_text('[]')
            import os
            argv = ["x", "--results", str(res), "--state", str(Path(tmp) / "s.json")]
            with mock.patch.object(sys, "argv", argv), \
                 mock.patch.dict(os.environ, {"GITHUB_REPOSITORY": "o/r", "GITHUB_STEP_SUMMARY": ""}):
                self.assertEqual(alert.main(), 0)


class RegulatorCheckTest(unittest.TestCase):
    NOW = datetime(2026, 11, 7, tzinfo=timezone.utc)

    def test_press_page_with_no_rows_is_a_failure(self):
        reg = check_feeds._load_regulator_module()
        spec = reg.RegulatorSpec("MX", "CNBV", "gob.mx/cnbv", "https://www.gob.mx/cnbv/archivo/prensa")
        with mock.patch.object(reg, "load_regulators", return_value=[spec]), \
             mock.patch.object(check_feeds, "_load_regulator_module", return_value=reg), \
             mock.patch.object(check_feeds, "fetch", return_value=(200, b"<html>nuevo diseno</html>", "")):
            [res] = check_feeds.check_regulators(self.NOW, 60)
        self.assertEqual(res.verdict, check_feeds.FAIL)
        self.assertIn("cambió el sitio", res.error)

    def test_quiet_google_search_is_not_a_failure(self):
        reg = check_feeds._load_regulator_module()
        spec = reg.RegulatorSpec("CL", "CMF", "cmfchile.cl")
        empty = b'<?xml version="1.0"?><rss version="2.0"><channel><title>x</title></channel></rss>'
        with mock.patch.object(reg, "load_regulators", return_value=[spec]), \
             mock.patch.object(check_feeds, "_load_regulator_module", return_value=reg), \
             mock.patch.object(check_feeds, "fetch", return_value=(200, empty, "")):
            [res] = check_feeds.check_regulators(self.NOW, 60)
        self.assertEqual(res.verdict, check_feeds.NO_RESULTS)


if __name__ == "__main__":
    unittest.main()
