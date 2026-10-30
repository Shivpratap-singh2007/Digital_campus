from app.services.priority_rules import evaluate_priority
from app.services.semantic import semantic_engine


def test_priority_rules_urgent_detection():
    """Test urgent hazard phrases trigger Urgent priority with plain-language explanation."""
    res = evaluate_priority("There is an exposed live wire hanging from the ceiling in the corridor.")
    assert res.suggested_priority == "Urgent review"
    assert res.matched_phrase == "exposed live wire"
    assert "electrocution hazard" in res.explanation
    assert res.is_ambiguous is False


def test_priority_rules_negation_handling():
    """Test negation prevents false urgency and flags ambiguous review."""
    # "no exposed wire" should not be marked Urgent
    res = evaluate_priority("Inspected the wall socket, there is no exposed wire found.")
    assert res.suggested_priority != "Urgent review"
    assert res.is_ambiguous is True
    assert "negation detected" in res.explanation.lower()


def test_priority_rules_historical_handling():
    """Test resolved or past statements are flagged as ambiguous / not urgent."""
    res = evaluate_priority("The pipe was already fixed yesterday by maintenance.")
    assert res.suggested_priority != "Urgent review"


def test_semantic_engine_fallback_or_evaluation():
    """Test semantic engine behaves gracefully whether model weights are present or blocked."""
    # Test that suggest_category does not raise unhandled exceptions
    result = semantic_engine.suggest_category(
        text="Water leaking from ceiling washbasin in hostel washroom",
        user_selected_category="Not sure",
    )
    assert isinstance(result, dict)
    assert "suggested_category" in result
    assert "reason" in result
    assert "is_ambiguous" in result

