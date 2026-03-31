from unittest.mock import MagicMock, patch
from typer.testing import CliRunner
from pedantic_troll.logic import app, display_troll_report
from pedantic_troll.schema import TrollReport, Grievance

runner = CliRunner()

def test_display_troll_report_success(capsys):
    report = TrollReport(
        intro="Listen here, amateur.",
        grievances=[
            Grievance(post_reference="p1", quote_snippet="abc", complaint="bad", severity="nit")
        ],
        verdict="Rewrite everything."
    )
    display_troll_report(report)
    captured = capsys.readouterr()
    assert "The Pedantic Troll Speaks" in captured.out
    assert "NIT" in captured.out
    assert "Rewrite everything." in captured.out

def test_display_troll_report_no_grievances(capsys):
    report = TrollReport(
        intro="Fine, I guess.",
        grievances=[],
        verdict="Carry on."
    )
    display_troll_report(report)
    captured = capsys.readouterr()
    assert "found nothing to complain about" in captured.out

@patch("pedantic_troll.logic.build_model")
@patch("pedantic_troll.logic.Agent")
@patch("pedantic_troll.logic.asyncio.run")
@patch("pedantic_troll.logic.track_llm_run")
def test_nitpick_command(mock_track_llm_run, mock_asyncio_run, mock_agent_class, mock_build_model, tmp_path):
    d1 = tmp_path / "post1.md"
    d1.write_text("content1")
    
    # Setup mock agent and result
    mock_agent = MagicMock()
    mock_agent_class.return_value = mock_agent
    
    mock_run_result = MagicMock()
    mock_run_result.output = TrollReport(
        intro="Troll intro",
        grievances=[],
        verdict="Troll verdict"
    )
    mock_asyncio_run.return_value = mock_run_result
    
    mock_run = MagicMock()
    mock_track_llm_run.return_value.__enter__.return_value = mock_run
    
    result = runner.invoke(app, [str(d1), "--no-llm"])
    
    assert result.exit_code == 0
    assert "Troll intro" in result.stdout
    assert "Troll verdict" in result.stdout
    mock_run.track.assert_called_once()

@patch("pedantic_troll.logic.list_vault_personas")
@patch("pedantic_troll.logic.build_model")
@patch("pedantic_troll.logic.Agent")
@patch("pedantic_troll.logic.asyncio.run")
@patch("pedantic_troll.logic.track_llm_run")
def test_nitpick_with_persona(mock_track, mock_async, mock_agent, mock_build, mock_list, tmp_path):
    from local_first_common.personas import BasePersona
    mock_list.return_value = [
        BasePersona(name="Grumpy", archetype="Troll", system_prompt="Be mean.")
    ]
    
    d1 = tmp_path / "post1.md"
    d1.write_text("content1")
    
    mock_run_result = MagicMock()
    mock_run_result.output = TrollReport(intro="Persona intro", grievances=[], verdict="Persona verdict")
    mock_async.return_value = mock_run_result
    
    result = runner.invoke(app, [str(d1), "--persona", "Grumpy", "--no-llm"])
    
    assert result.exit_code == 0
    assert "Persona intro" in result.stdout
