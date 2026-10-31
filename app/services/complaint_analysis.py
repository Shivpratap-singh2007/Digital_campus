import json
import logging
from flask import current_app
from app.extensions import db
from app.models.complaint import Complaint, AnalysisResult
from app.services.semantic import semantic_engine
from app.services.priority_rules import evaluate_priority

logger = logging.getLogger(__name__)


def run_complaint_analysis(complaint: Complaint) -> bool:
    """
    Executes analysis pipeline for a complaint:
    1. Evaluates versioned explainable priority rules (with negation and historical detection).
    2. Runs semantic categorization (if sentence-transformers model is available).
    3. Flags ambiguous or weak matches for handler review.
    4. Updates or creates AnalysisResult and updates Complaint state.
    
    Guarantees:
    - If analysis raises an error, the complaint remains saved and is marked 'needs_review'.
    - If embedding model is unavailable, rules still run and the semantic status is explicitly marked unavailable.
    """
    try:
        combined_text = f"{complaint.title}\n{complaint.description}"
        
        # 1. Versioned priority rules
        prio_result = evaluate_priority(
            text=combined_text,
            submission_type=complaint.submission_type,
        )

        # 2. Semantic category suggestions
        cat_result = semantic_engine.suggest_category(
            text=combined_text,
            user_selected_category=complaint.user_category,
        )

        model_name = (
            current_app.config.get("MODEL_NAME", "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")
            if cat_result["is_available"]
            else f"Unavailable ({semantic_engine.load_error or 'Environment Policy'})"
        )
        analysis_version = current_app.config.get("ANALYSIS_VERSION", "1.0.0")

        # Determine overall ambiguity
        is_ambiguous = prio_result.is_ambiguous or cat_result["is_ambiguous"]

        # 3. Save or update AnalysisResult
        analysis = complaint.analysis_result
        if not analysis:
            analysis = AnalysisResult(complaint_id=complaint.id)
            db.session.add(analysis)

        analysis.model_identifier = model_name
        analysis.analysis_version = analysis_version
        analysis.suggested_category = cat_result["suggested_category"]
        analysis.category_similarity = cat_result["similarity"]
        analysis.category_reason = cat_result["reason"]
        analysis.suggested_priority = prio_result.suggested_priority
        analysis.priority_reason = prio_result.explanation
        analysis.matched_phrase = prio_result.matched_phrase
        analysis.is_ambiguous = is_ambiguous
        analysis.is_semantic_available = cat_result["is_available"]
        if cat_result.get("embedding"):
            analysis.embedding_json = json.dumps(cat_result["embedding"])

        # Update complaint fields
        complaint.suggested_category = cat_result["suggested_category"]
        complaint.suggested_priority = prio_result.suggested_priority
        complaint.analysis_state = "needs_review" if is_ambiguous else "completed"

        db.session.commit()
        logger.info(f"Analysis completed for Complaint #{complaint.id}: state={complaint.analysis_state}")
        return True

    except Exception as e:
        logger.exception(f"Analysis failed for Complaint #{complaint.id}: {e}")
        db.session.rollback()
        try:
            # Preserve complaint and mark as needs_review
            comp = db.session.get(Complaint, complaint.id)
            if comp:
                comp.analysis_state = "needs_review"
                db.session.commit()
        except Exception:
            pass
        return False
