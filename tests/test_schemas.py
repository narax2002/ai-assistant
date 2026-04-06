from schemas.research import AgentResult, ResearchRequest, ResearchResponse


def test_request_auto_generates_id():
    req = ResearchRequest(query="test")
    assert req.request_id
    assert len(req.request_id) == 12


def test_request_accepts_custom_id():
    req = ResearchRequest(query="test", request_id="custom123")
    assert req.request_id == "custom123"


def test_two_requests_have_different_ids():
    a = ResearchRequest(query="a")
    b = ResearchRequest(query="b")
    assert a.request_id != b.request_id


def test_response_format_discord():
    resp = ResearchResponse(
        request_id="abc",
        summary="요약",
        comparison="비교 내용",
        next_actions="행동",
        sources="출처 목록",
    )
    text = resp.format_discord()
    assert "**핵심 요약**" in text
    assert "**비교**" in text
    assert "**다음 행동**" in text
    assert "**출처**" in text


def test_agent_result_success():
    r = AgentResult(agent_name="research", output="ok", elapsed_seconds=1.5, success=True)
    assert r.success
    assert r.error is None


def test_agent_result_failure():
    r = AgentResult(
        agent_name="analyst", output="fallback", elapsed_seconds=2.0, success=False, error="timeout"
    )
    assert not r.success
    assert r.error == "timeout"


def test_response_includes_agent_results():
    results = [
        AgentResult(agent_name="research", output="ok", elapsed_seconds=1.0, success=True),
    ]
    resp = ResearchResponse(
        request_id="abc",
        summary="s",
        comparison="c",
        next_actions="n",
        sources="src",
        agent_results=results,
        total_elapsed_seconds=3.5,
    )
    assert len(resp.agent_results) == 1
    assert resp.total_elapsed_seconds == 3.5
