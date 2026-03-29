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

@patch("pedantic_troll.logic.resolve_provider")
@patch("pedantic_troll.logic.timed_run")
def test_nitpick_command(mock_timed_run, mock_resolve_provider, tmp_path):
    d1 = tmp_path / "post1.md"
    d1.write_text("content1")
    
    mock_llm = MagicMock()
    mock_llm.model = "mock-model"
    mock_llm.complete.return_value = TrollReport(
        intro="Troll intro",
        grievances=[],
        verdict="Troll verdict"
    )
    mock_resolve_provider.return_value = mock_llm
    
    mock_timed_run.return_value.__enter__.return_value = MagicMock()
    
    result = runner.invoke(app, [str(d1), "--no-llm"])
    
    assert result.exit_code == 0
    assert "Troll intro" in result.stdout
    assert "Troll verdict" in result.stdout
