"""
Unit tests for SRE Autonomous Agent

Tests cover:
- State creation and manipulation helpers
- Postmortem generation (pure Python, no LLM)
- Guardrails loading and validation
- Approval manager CRUD operations
- Triage / hypothesis / remediation agents with mocked LLM
"""

import json
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def make_state(**kwargs):
    """Return a minimal IncidentState dict for testing."""
    from app.graph.state import create_initial_state

    alert = {
        "status": "firing",
        "commonLabels": {
            "alertname": "PodCrashLooping",
            "namespace": "test",
            "pod": "api-xyz-123",
            "deployment": "api",
        },
        "commonAnnotations": {
            "description": "Pod is crashing",
        },
    }
    state = create_initial_state(alert, "INC-TEST-001")
    state.update(kwargs)
    return state


# ---------------------------------------------------------------------------
# State helpers
# ---------------------------------------------------------------------------


class TestStateHelpers:
    def test_create_initial_state_fields(self):
        from app.graph.state import create_initial_state

        alert = {"commonLabels": {"alertname": "TestAlert"}}
        state = create_initial_state(alert, "INC-0001")

        assert state["incident_id"] == "INC-0001"
        assert state["alert"] == alert
        assert state["incident_type"] is None
        assert state["severity"] is None
        assert state["affected_resources"] == {}
        assert state["hypotheses"] == []
        assert state["diagnostics"] == []
        assert state["root_cause"] is None
        assert state["remediation_plan"] is None
        assert state["alternative_plans"] == []
        assert state["approved"] is False
        assert state["approval_id"] is None
        assert state["remediation_executed"] is False
        assert state["postmortem"] is None
        assert state["errors"] == []
        assert len(state["timeline"]) == 1
        assert state["timeline"][0]["agent"] == "system"

    def test_add_timeline_entry(self):
        from app.graph.state import add_timeline_entry

        state = make_state()
        initial_len = len(state["timeline"])

        state = add_timeline_entry(state, "triage", "classified", "CrashLoopBackOff")

        assert len(state["timeline"]) == initial_len + 1
        last = state["timeline"][-1]
        assert last["agent"] == "triage"
        assert last["action"] == "classified"
        assert last["details"] == "CrashLoopBackOff"

    def test_updated_at_advances(self):
        from app.graph.state import add_timeline_entry
        import time

        state = make_state()
        old_ts = state["updated_at"]
        time.sleep(0.01)
        state = add_timeline_entry(state, "test", "action", "details")
        assert state["updated_at"] >= old_ts


# ---------------------------------------------------------------------------
# Postmortem agent (pure Python – no LLM required)
# ---------------------------------------------------------------------------


class TestPostmortemAgent:
    def _full_state(self):
        from app.graph.state import Hypothesis, DiagnosticResult, RemediationAction

        state = make_state(
            incident_type="CrashLoopBackOff",
            severity="critical",
            affected_resources={"namespace": "test", "pod": "api-xyz", "deployment": "api"},
            root_cause="Missing DATABASE_URL environment variable",
            hypotheses=[
                Hypothesis(
                    description="Missing env var causes crash on startup",
                    confidence=0.9,
                    category="config",
                )
            ],
            diagnostics=[
                DiagnosticResult(
                    source="pod_logs",
                    data={"output": "Error: DATABASE_URL not set"},
                    timestamp="2025-01-01T00:00:00",
                )
            ],
            remediation_plan=RemediationAction(
                action_type="config_change",
                description="Add DATABASE_URL to deployment env",
                risk_level="low",
                requires_pr=True,
                command="kubectl set env deployment/api DATABASE_URL=...",
                estimated_impact="Resolves crash loop",
            ),
            alternative_plans=[],
        )
        return state

    def test_postmortem_contains_key_sections(self):
        from app.agents.postmortem import postmortem_agent

        state = self._full_state()
        result = postmortem_agent(state)

        pm = result["postmortem"]
        assert pm is not None
        assert "INC-TEST-001" in pm
        assert "CrashLoopBackOff" in pm
        assert "DATABASE_URL" in pm
        assert "Remediation" in pm
        assert "Timeline" in pm

    def test_postmortem_timeline_entry_added(self):
        from app.agents.postmortem import postmortem_agent

        state = self._full_state()
        initial_len = len(state["timeline"])
        result = postmortem_agent(state)

        assert len(result["timeline"]) == initial_len + 1
        assert result["timeline"][-1]["agent"] == "postmortem"

    def test_generate_preventive_measures_crashloop(self):
        from app.agents.postmortem import generate_preventive_measures

        state = self._full_state()
        measures = generate_preventive_measures(state)

        assert "environment" in measures.lower() or "config" in measures.lower()

    def test_generate_lessons_learned(self):
        from app.agents.postmortem import generate_lessons_learned

        state = self._full_state()
        lessons = generate_lessons_learned(state)

        assert len(lessons) > 0
        assert "staging" in lessons.lower() or "automated" in lessons.lower()


# ---------------------------------------------------------------------------
# Guardrails / remediation agent helpers
# ---------------------------------------------------------------------------


class TestGuardrails:
    def test_load_guardrails_returns_dict(self):
        from app.agents.remediation import load_guardrails

        guardrails = load_guardrails()
        assert isinstance(guardrails, dict)
        assert "forbidden_actions" in guardrails
        assert "allowed_namespaces" in guardrails

    def test_forbidden_action_rejected(self):
        from app.agents.remediation import validate_against_guardrails
        from app.graph.state import RemediationAction

        action = RemediationAction(
            action_type="delete_namespace",
            description="Delete the namespace",
            risk_level="high",
            requires_pr=False,
            command=None,
            estimated_impact="Destructive",
        )
        is_valid, msg = validate_against_guardrails(action)
        assert is_valid is False
        assert "forbidden" in msg.lower()

    def test_allowed_action_passes(self):
        from app.agents.remediation import validate_against_guardrails
        from app.graph.state import RemediationAction

        action = RemediationAction(
            action_type="config_change",
            description="Add env variable",
            risk_level="low",
            requires_pr=True,
            command=None,
            estimated_impact="Minimal",
        )
        is_valid, msg = validate_against_guardrails(action)
        assert is_valid is True


# ---------------------------------------------------------------------------
# Approval manager
# ---------------------------------------------------------------------------


class TestApprovalManager:
    def _make_manager(self, tmp_path):
        from app.approval.manager import ApprovalManager

        return ApprovalManager(storage_dir=str(tmp_path))

    def _make_state(self):
        return make_state(
            incident_type="CrashLoopBackOff",
            root_cause="Missing env var",
            remediation_plan={
                "action_type": "config_change",
                "description": "Add DATABASE_URL",
                "risk_level": "low",
                "requires_pr": True,
                "command": None,
                "estimated_impact": "Resolves crash",
            },
        )

    def test_create_and_retrieve(self, tmp_path):
        manager = self._make_manager(tmp_path)
        state = self._make_state()

        req = manager.create_approval_request(state)
        assert req.incident_id == "INC-TEST-001"
        assert req.status == "pending"

        retrieved = manager.get_request("INC-TEST-001")
        assert retrieved is not None
        assert retrieved.incident_id == "INC-TEST-001"

    def test_approve(self, tmp_path):
        manager = self._make_manager(tmp_path)
        state = self._make_state()
        manager.create_approval_request(state)

        result = manager.approve("INC-TEST-001", approved_by="sre-team")
        assert result is True
        assert manager.is_approved("INC-TEST-001") is True

    def test_reject(self, tmp_path):
        manager = self._make_manager(tmp_path)
        state = self._make_state()
        manager.create_approval_request(state)

        result = manager.reject("INC-TEST-001", reason="Too risky in prod")
        assert result is True
        assert manager.is_approved("INC-TEST-001") is False
        req = manager.get_request("INC-TEST-001")
        assert req.status == "rejected"
        assert req.rejection_reason == "Too risky in prod"

    def test_list_pending(self, tmp_path):
        manager = self._make_manager(tmp_path)

        for i in range(3):
            s = make_state(
                incident_type="CrashLoopBackOff",
                root_cause="err",
                remediation_plan={
                    "action_type": "config_change",
                    "description": "fix",
                    "risk_level": "low",
                    "requires_pr": False,
                    "command": None,
                    "estimated_impact": "minor",
                },
            )
            s["incident_id"] = f"INC-TEST-{i:03d}"
            manager.create_approval_request(s)

        # Approve one
        manager.approve("INC-TEST-001")

        pending = manager.list_pending()
        assert len(pending) == 2
        ids = {r.incident_id for r in pending}
        assert "INC-TEST-001" not in ids

    def test_get_nonexistent_returns_none(self, tmp_path):
        manager = self._make_manager(tmp_path)
        assert manager.get_request("DOES-NOT-EXIST") is None
        assert manager.is_approved("DOES-NOT-EXIST") is False

    def test_get_approval_status(self, tmp_path):
        manager = self._make_manager(tmp_path)
        state = self._make_state()
        manager.create_approval_request(state)

        assert manager.get_approval_status("INC-TEST-001") == "pending"
        manager.approve("INC-TEST-001")
        assert manager.get_approval_status("INC-TEST-001") == "approved"
        assert manager.get_approval_status("NO-SUCH") is None


# ---------------------------------------------------------------------------
# Triage agent (mocked LLM)
# ---------------------------------------------------------------------------


class TestTriageAgent:
    def _make_llm_response(self, content: str):
        mock_response = MagicMock()
        mock_response.content = content
        return mock_response

    def test_triage_parses_valid_json(self):
        from app.agents.triage import triage_agent

        llm_json = json.dumps({
            "incident_type": "CrashLoopBackOff",
            "severity": "critical",
            "affected_resources": {"namespace": "payments", "pod": "api-xyz"},
            "reasoning": "Pod restart loop",
        })

        with patch("app.agents.triage.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(llm_json)
            state = make_state()
            result = triage_agent(state)

        assert result["incident_type"] == "CrashLoopBackOff"
        assert result["severity"] == "critical"
        assert result["affected_resources"]["namespace"] == "payments"

    def test_triage_falls_back_on_invalid_json(self):
        from app.agents.triage import triage_agent

        with patch("app.agents.triage.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response("not json at all")
            state = make_state()
            result = triage_agent(state)

        # Should use fallback values from alert labels
        assert result["incident_type"] is not None
        assert result["severity"] is not None

    def test_triage_adds_timeline_entry(self):
        from app.agents.triage import triage_agent

        llm_json = json.dumps({
            "incident_type": "OOMKilled",
            "severity": "high",
            "affected_resources": {},
            "reasoning": "OOM",
        })

        with patch("app.agents.triage.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(llm_json)
            state = make_state()
            initial_len = len(state["timeline"])
            result = triage_agent(state)

        assert len(result["timeline"]) == initial_len + 1
        assert result["timeline"][-1]["agent"] == "triage"


# ---------------------------------------------------------------------------
# Hypothesis agent (mocked LLM)
# ---------------------------------------------------------------------------


class TestHypothesisAgent:
    def _make_llm_response(self, content: str):
        mock_response = MagicMock()
        mock_response.content = content
        return mock_response

    def test_hypothesis_parses_valid_json(self):
        from app.agents.hypothesis import hypothesis_agent

        hypotheses_json = json.dumps([
            {"description": "Missing DATABASE_URL", "confidence": 0.9, "category": "config"},
            {"description": "Probe failure", "confidence": 0.5, "category": "code"},
        ])

        with patch("app.agents.hypothesis.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(hypotheses_json)
            state = make_state(incident_type="CrashLoopBackOff", severity="critical")
            result = hypothesis_agent(state)

        assert len(result["hypotheses"]) == 2
        assert result["hypotheses"][0]["description"] == "Missing DATABASE_URL"
        assert result["hypotheses"][0]["confidence"] == 0.9

    def test_hypothesis_fallback_on_bad_json(self):
        from app.agents.hypothesis import hypothesis_agent

        with patch("app.agents.hypothesis.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response("bad response")
            state = make_state(incident_type="CrashLoopBackOff", severity="critical")
            result = hypothesis_agent(state)

        # Should have at least one fallback hypothesis
        assert len(result["hypotheses"]) >= 1

    def test_hypothesis_adds_timeline_entry(self):
        from app.agents.hypothesis import hypothesis_agent

        hypotheses_json = json.dumps([
            {"description": "Config error", "confidence": 0.8, "category": "config"},
        ])

        with patch("app.agents.hypothesis.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(hypotheses_json)
            state = make_state(incident_type="CrashLoopBackOff", severity="critical")
            initial_len = len(state["timeline"])
            result = hypothesis_agent(state)

        assert len(result["timeline"]) == initial_len + 1
        assert result["timeline"][-1]["agent"] == "hypothesis"


# ---------------------------------------------------------------------------
# Remediation agent (mocked LLM)
# ---------------------------------------------------------------------------


class TestRemediationAgent:
    def _make_llm_response(self, content: str):
        mock_response = MagicMock()
        mock_response.content = content
        return mock_response

    def _state_with_root_cause(self):
        from app.graph.state import DiagnosticResult

        return make_state(
            incident_type="CrashLoopBackOff",
            severity="critical",
            affected_resources={"namespace": "test", "deployment": "api"},
            root_cause="Missing DATABASE_URL environment variable",
            diagnostics=[
                DiagnosticResult(
                    source="pod_logs",
                    data={"output": "ERROR: DATABASE_URL not set"},
                    timestamp="2025-01-01T00:00:00",
                )
            ],
        )

    def test_remediation_parses_valid_json(self):
        from app.agents.remediation import remediation_agent

        plan_json = json.dumps({
            "primary": {
                "action_type": "config_change",
                "description": "Add DATABASE_URL to deployment env",
                "risk_level": "low",
                "requires_pr": True,
                "command": "kubectl set env deployment/api DATABASE_URL=...",
                "estimated_impact": "Resolves crash loop",
            },
            "alternatives": [],
        })

        with patch("app.agents.remediation.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(plan_json)
            state = self._state_with_root_cause()
            result = remediation_agent(state)

        assert result["remediation_plan"] is not None
        assert result["remediation_plan"]["action_type"] == "config_change"
        assert result["remediation_plan"]["risk_level"] == "low"

    def test_remediation_blocked_by_guardrails(self):
        from app.agents.remediation import remediation_agent

        plan_json = json.dumps({
            "primary": {
                "action_type": "delete_namespace",
                "description": "Delete namespace",
                "risk_level": "high",
                "requires_pr": False,
                "command": "kubectl delete ns test",
                "estimated_impact": "Destructive",
            },
            "alternatives": [],
        })

        with patch("app.agents.remediation.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response(plan_json)
            state = self._state_with_root_cause()
            result = remediation_agent(state)

        assert result["remediation_plan"] is None
        assert any("blocked" in e.lower() or "forbidden" in e.lower() for e in result["errors"])

    def test_remediation_fallback_on_bad_json(self):
        from app.agents.remediation import remediation_agent

        with patch("app.agents.remediation.ChatOpenAI") as MockLLM:
            MockLLM.return_value.invoke.return_value = self._make_llm_response("no json here")
            state = self._state_with_root_cause()
            result = remediation_agent(state)

        # Fallback plan type is manual_investigation which is not in forbidden list
        assert result["remediation_plan"] is not None
        assert result["remediation_plan"]["action_type"] == "manual_investigation"
