from pedantic_troll.prompts import build_system_prompt
from pedantic_troll.logic import PedanticTrollError, ModelBuildError, NitpickRunError


def test_build_system_prompt():
    prompt = build_system_prompt("Test premise", "You are a Troll.")
    assert "Test premise" in prompt
    assert "You are a Troll." in prompt


class TestTypedErrors:
    def test_error_hierarchy(self):
        assert issubclass(ModelBuildError, PedanticTrollError)
        assert issubclass(NitpickRunError, PedanticTrollError)

    def test_model_build_error_message(self):
        err = ModelBuildError("provider unavailable")
        assert "provider unavailable" in str(err)

    def test_nitpick_run_error_message(self):
        err = NitpickRunError("timed out")
        assert "timed out" in str(err)
