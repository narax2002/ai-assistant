"""Tests for llm/base.py — error hierarchy and ChatUsage."""

from llm.base import ChatUsage, LLMConnectionError, LLMError, LLMTimeoutError


def test_llm_error_is_not_transient():
    assert LLMError.transient is False


def test_llm_timeout_error_is_transient():
    assert LLMTimeoutError.transient is True


def test_llm_connection_error_is_transient():
    assert LLMConnectionError.transient is True


def test_llm_connection_error_inherits_llm_error():
    assert issubclass(LLMConnectionError, LLMError)


def test_chat_usage_defaults():
    usage = ChatUsage()
    assert usage.prompt_tokens == 0
    assert usage.completion_tokens == 0
    assert usage.total_tokens == 0


def test_chat_usage_total():
    usage = ChatUsage(prompt_tokens=100, completion_tokens=50)
    assert usage.total_tokens == 150
