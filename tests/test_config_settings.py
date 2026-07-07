import os
import pytest
from config.settings import Settings, settings
from agent.llm import get_chat_model, get_embedding_model


def test_settings_load_successfully(monkeypatch):
    """Verify that settings can be loaded successfully with placeholder variables."""
    monkeypatch.setenv("LLM_PROVIDER", "openai")
    monkeypatch.setenv("OPENAI_API_KEY", "dummy_key")
    monkeypatch.setenv("EMBEDDING_MODEL", "text-embedding-3-small")
    
    # Reload Settings
    new_settings = Settings()
    assert new_settings.llm_provider == "openai"
    assert new_settings.openai_api_key == "dummy_key"
    assert new_settings.embedding_model == "text-embedding-3-small"


def test_get_chat_model_openai_construction(monkeypatch):
    """Verify that get_chat_model constructs an OpenAI ChatModel object without making real API calls."""
    monkeypatch.setenv("ENV", "production") # Avoid triggering the fake/test fallback
    monkeypatch.setattr(settings, "openai_api_key", "sk-dummykeyherefortestingconstruction")
    monkeypatch.setattr(settings, "llm_provider", "openai")
    
    # Import ChatOpenAI from langchain_openai to verify type
    from langchain_openai import ChatOpenAI
    
    model = get_chat_model(provider="openai", model="gpt-4o-mini")
    
    assert isinstance(model, ChatOpenAI)
    assert model.model_name == "gpt-4o-mini"
    assert model.openai_api_key.get_secret_value() == "sk-dummykeyherefortestingconstruction"


def test_get_embedding_model_construction(monkeypatch):
    """Verify that get_embedding_model constructs an OpenAIEmbeddings object without making real API calls."""
    monkeypatch.setenv("ENV", "production") # Avoid triggering the fake/test fallback
    monkeypatch.setattr(settings, "openai_api_key", "sk-dummykeyherefortestingconstruction")
    monkeypatch.setattr(settings, "embedding_model", "text-embedding-3-small")
    
    from langchain_openai import OpenAIEmbeddings
    
    emb = get_embedding_model()
    
    assert isinstance(emb, OpenAIEmbeddings)
    assert emb.model == "text-embedding-3-small"
    assert emb.openai_api_key.get_secret_value() == "sk-dummykeyherefortestingconstruction"

