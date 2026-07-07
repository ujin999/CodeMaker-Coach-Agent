from agent.prompts.problem_generation import build_problem_generation_prompt
from agent.prompts.testcase_generation import build_testcase_generation_prompt
from agent.prompts.hint_generation import build_hint_generation_prompt
from agent.prompts.feedback import build_feedback_prompt
from agent.prompts.validation import build_problem_validation_prompt


def test_problem_generation_prompt_has_korean_instruction():
    """Verify that problem generation prompt contains Korean output instruction."""
    prompt = build_problem_generation_prompt()
    system_text = prompt.messages[0].prompt.template.lower()
    user_text = prompt.messages[1].prompt.template.lower()
    
    assert "korean" in system_text or "한국어" in system_text
    assert "korean" in user_text or "한국어" in user_text


def test_testcase_generation_prompt_has_korean_instruction():
    """Verify that testcase generation prompt contains Korean output instruction."""
    prompt = build_testcase_generation_prompt()
    system_text = prompt.messages[0].prompt.template.lower()
    user_text = prompt.messages[1].prompt.template.lower()
    
    assert "korean" in system_text or "한국어" in system_text
    assert "korean" in user_text or "한국어" in user_text


def test_hint_generation_prompt_has_korean_instruction():
    """Verify that hint generation prompt contains Korean output instruction."""
    prompt = build_hint_generation_prompt()
    system_text = prompt.messages[0].prompt.template.lower()
    user_text = prompt.messages[1].prompt.template.lower()
    
    assert "korean" in system_text or "한국어" in system_text
    assert "korean" in user_text or "한국어" in user_text


def test_feedback_prompt_has_korean_instruction():
    """Verify that feedback prompt contains Korean output instruction."""
    prompt = build_feedback_prompt()
    system_text = prompt.messages[0].prompt.template.lower()
    user_text = prompt.messages[1].prompt.template.lower()
    
    assert "korean" in system_text or "한국어" in system_text
    assert "korean" in user_text or "한국어" in user_text


def test_validation_prompt_has_korean_instruction():
    """Verify that validation prompt contains Korean output instruction."""
    prompt = build_problem_validation_prompt()
    system_text = prompt.messages[0].prompt.template.lower()
    user_text = prompt.messages[1].prompt.template.lower()
    
    assert "korean" in system_text or "한국어" in system_text
    assert "korean" in user_text or "한국어" in user_text
