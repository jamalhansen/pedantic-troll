from pedantic_troll.prompts import build_system_prompt

def test_build_system_prompt():
    prompt = build_system_prompt("Test premise")
    assert "Test premise" in prompt
    assert "Pedantic Troll" in prompt
