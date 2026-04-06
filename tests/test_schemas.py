from schemas.research import ResearchRequest, ResearchResponse


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
    assert "요약" in text
    assert "비교 내용" in text
    assert "행동" in text
    assert "출처 목록" in text
