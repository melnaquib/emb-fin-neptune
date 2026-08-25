from __future__ import annotations

import json

from typer.testing import CliRunner

from ivd.cli import app

runner = CliRunner()


def test_fetch_json_prints_valid_json_for_both_invoices():
    result = runner.invoke(app, ["fetch", "--source", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert {item["id"] for item in payload} == {"INV-001", "INV-002"}


def test_triage_puts_both_fixture_invoices_in_calling():
    result = runner.invoke(app, ["triage", "--source", "json"])
    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    states = {item["invoice_id"]: item["state"] for item in payload}
    assert states == {"INV-001": "calling", "INV-002": "calling"}
