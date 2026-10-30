import json
import logging
from typing import Any
import numpy as np
from flask import current_app

logger = logging.getLogger(__name__)

# Representative examples for each category to compute reference centroid embeddings
CATEGORY_EXAMPLES = {
    "Infrastructure": [
        "Broken window pane in classroom and broken door lock",
        "Elevator stuck between floors or lift not working",
        "Water pipe burst causing flooding in corridor",
        "Ceiling plaster falling or cracked wall in building",
        "Broken chairs and broken desks in lecture hall",
        "Street light not working on walkway or campus grounds",
        "Air conditioning unit leaking or broken heating ventilation",
    ],
    "Sanitation": [
        "Restrooms dirty and no running water in taps",
        "Garbage overflowing in dustbins outside canteen",
        "Sewage leak causing terrible odor in dormitory basement",
        "Pest infestation including cockroaches and rats in hostel",
        "Washbasin clogged and drain blocked in bathroom",
        "Drinking water cooler contaminated or foul smelling",
    ],
    "Academics": [
        "Projector and audio microphone not working in lecture theater",
        "Lab equipment faulty during physics experiment",
        "Classroom schedule overlap and room double booking",
        "Library book issue scanner malfunction",
        "Exam hall seating arrangement missing roll numbers",
        "Teaching assistant not showing up for scheduled tutorial",
    ],
    "Student services": [
        "Hostel room allocation delay or mess fee payment issue",
        "Cafeteria food quality poor or stale meal served",
        "Student identity card printing delayed at admin office",
        "Scholarship disbursement status inquiry",
        "Campus shuttle bus arriving late or skipping stops",
        "Gym equipment broken in sports center",
    ],
    "IT/connectivity": [
        "Campus Wi-Fi disconnected or extremely slow in hostel",
        "Ethernet port dead in computer science laboratory",
        "Student portal login error and password reset not working",
        "Print quota not updating after recharge",
        "Firewall blocking academic research repository access",
        "Server unreachable for campus intranet portal",
    ],
    "Other": [
        "General campus suggestion or miscellaneous feedback",
        "Request for new recycling bin installation",
        "Lost and found item inquiry",
        "Suggestion for campus cultural fest organization",
    ],
}


class SemanticEngine:
    """
    Manages embedding model loading, embedding caching,
    semantic category suggestions, and related complaint retrieval.
    Gracefully handles environments where sentence-transformers or torch native DLLs are unavailable.
    """
    def __init__(self):
        self._model = None
        self._load_attempted = False
        self._load_error: str | None = None
        self._category_embeddings: dict[str, np.ndarray] = {}

    @property
    def is_available(self) -> bool:
        self._ensure_loaded()
        return self._model is not None

    @property
    def load_error(self) -> str | None:
        self._ensure_loaded()
        return self._load_error

    def _ensure_loaded(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True

        # Do not trigger a model download during unit testing
        try:
            if current_app and current_app.config.get("TESTING"):
                self._model = None
                self._load_error = "Testing mode: Model download skipped for unit tests."
                return
        except Exception:
            pass

        model_name = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        try:
            import os
            # Prevent hanging network retries in offline / sandbox environments
            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")

            from sentence_transformers import SentenceTransformer
            # Try loading locally first without blocking network retries
            self._model = SentenceTransformer(model_name, local_files_only=True)
            self._load_error = None
            self._precompute_category_embeddings()
            logger.info("Semantic embedding model successfully loaded and cached.")
        except Exception as e:
            self._model = None
            self._load_error = f"{type(e).__name__}: {str(e)}"
            logger.warning(
                f"Embedding model unavailable ({self._load_error}). "
                "Semantic AI suggestions will be labeled as unavailable. Rule-based evaluation will proceed."
            )

    def _precompute_category_embeddings(self) -> None:
        """Precompute and cache normalized centroid embeddings for each category."""
        if self._model is None:
            return
        for cat, examples in CATEGORY_EXAMPLES.items():
            embeddings = self._model.encode(examples, normalize_embeddings=True)
            # Centroid mean embedding normalized to unit sphere
            centroid = np.mean(embeddings, axis=0)
            norm = np.linalg.norm(centroid)
            if norm > 0:
                centroid = centroid / norm
            self._category_embeddings[cat] = centroid

    def encode_text(self, text: str) -> np.ndarray | None:
        """Encodes text to a normalized embedding vector."""
        if not self.is_available or self._model is None:
            return None
        try:
            embedding = self._model.encode([text], normalize_embeddings=True)[0]
            return np.array(embedding, dtype=np.float32)
        except Exception as e:
            logger.error(f"Failed to encode text: {e}")
            return None

    def suggest_category(
        self, text: str, user_selected_category: str
    ) -> dict[str, Any]:
        """
        Suggests a category based on semantic cosine similarity against precomputed category representations.
        Returns dict with suggested_category, similarity, reason, is_ambiguous, is_available.
        """
        if not self.is_available:
            return {
                "suggested_category": None,
                "similarity": None,
                "reason": "Semantic AI model unavailable in current environment. Final category requires handler review.",
                "is_ambiguous": True,
                "is_available": False,
                "embedding": None,
            }

        embedding = self.encode_text(text)
        if embedding is None:
            return {
                "suggested_category": None,
                "similarity": None,
                "reason": "Failed to generate semantic embedding.",
                "is_ambiguous": True,
                "is_available": False,
                "embedding": None,
            }

        # Calculate cosine similarity with each category centroid
        scores: dict[str, float] = {}
        for cat, centroid in self._category_embeddings.items():
            # Normalized vectors dot product = cosine similarity
            sim = float(np.dot(embedding, centroid))
            scores[cat] = sim

        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        top_cat, top_score = sorted_cats[0]
        second_cat, second_score = sorted_cats[1] if len(sorted_cats) > 1 else ("", 0.0)

        # Configured thresholds
        similarity_threshold = current_app.config.get("SIMILARITY_THRESHOLD", 0.55) if current_app else 0.55
        ambiguity_margin = current_app.config.get("AMBIGUITY_MARGIN", 0.08) if current_app else 0.08

        is_weak = top_score < similarity_threshold
        is_close = (top_score - second_score) < ambiguity_margin
        is_ambiguous = is_weak or is_close

        reason_parts = [
            f"Cosine similarity score: {top_score:.3f} to '{top_cat}' reference cluster."
        ]
        if is_weak:
            reason_parts.append(f"Score is below the standard threshold ({similarity_threshold}); flagged for review.")
        elif is_close:
            reason_parts.append(
                f"Close match with '{second_cat}' (score: {second_score:.3f}, diff < {ambiguity_margin}); flagged for review."
            )
        else:
            reason_parts.append("Distinct semantic cluster match.")

        if user_selected_category and user_selected_category != "Not sure":
            if user_selected_category != top_cat:
                reason_parts.append(
                    f"User selected '{user_selected_category}' while AI suggested '{top_cat}'."
                )

        reason_parts.append("Note: Similarity is not a calibrated confidence percentage.")

        return {
            "suggested_category": top_cat,
            "similarity": round(top_score, 4),
            "reason": " ".join(reason_parts),
            "is_ambiguous": is_ambiguous,
            "is_available": True,
            "embedding": embedding.tolist(),
        }

    def find_related_complaints(
        self,
        current_complaint_id: int,
        current_embedding_json: str | None,
        current_building: str,
        current_room: str | None,
        candidate_complaints: list[Any],
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """
        Ranks candidate complaints for potential linkage or recurrence:
        - Uses cosine similarity between complaint embeddings.
        - Boosts / notes structured location (same building, same room).
        - Labels resolved issues as 'possible recurrence'.
        """
        if not candidate_complaints:
            return []

        curr_vector = None
        if current_embedding_json:
            try:
                curr_vector = np.array(json.loads(current_embedding_json), dtype=np.float32)
            except Exception:
                curr_vector = None

        results = []
        for c in candidate_complaints:
            if c.id == current_complaint_id:
                continue

            sim_score = 0.0
            match_reasons = []

            # 1. Location match check
            same_building = (
                current_building
                and c.building
                and current_building.strip().lower() == c.building.strip().lower()
            )
            same_room = False
            if current_room and c.room:
                same_room = current_room.strip().lower() == c.room.strip().lower()

            if same_building and same_room:
                match_reasons.append(f"Exact location: {c.building}, Room {c.room}")
            elif same_building:
                match_reasons.append(f"Same building: {c.building}")

            # 2. Text embedding similarity
            if curr_vector is not None and c.analysis_result and c.analysis_result.embedding_json:
                try:
                    c_vec = np.array(json.loads(c.analysis_result.embedding_json), dtype=np.float32)
                    norm_curr = np.linalg.norm(curr_vector)
                    norm_c = np.linalg.norm(c_vec)
                    if norm_curr > 0 and norm_c > 0:
                        sim_score = float(np.dot(curr_vector, c_vec) / (norm_curr * norm_c))
                except Exception:
                    sim_score = 0.0

            if sim_score > 0:
                match_reasons.append(f"Semantic similarity: {sim_score:.2f}")

            # Check if linked to an issue that was resolved
            is_possible_recurrence = False
            linked_issue_status = None
            if c.issue_link and c.issue_link.issue:
                linked_issue_status = c.issue_link.issue.status
                if linked_issue_status == "resolved":
                    is_possible_recurrence = True
                    match_reasons.append("Matches previously RESOLVED issue (Possible Recurrence)")

            # Overall relevance composite score for ranking
            # Base similarity + 0.15 for same building + 0.20 for same room
            composite_rank = sim_score
            if same_building:
                composite_rank += 0.15
            if same_room:
                composite_rank += 0.20

            # Include if there is meaningful similarity or location overlap
            if sim_score >= 0.40 or (same_building and (same_room or sim_score >= 0.30)):
                results.append({
                    "complaint": c,
                    "similarity": round(sim_score, 3),
                    "composite_rank": composite_rank,
                    "same_building": same_building,
                    "same_room": same_room,
                    "is_possible_recurrence": is_possible_recurrence,
                    "match_details": "; ".join(match_reasons) if match_reasons else "General proximity",
                })

        # Sort by composite rank descending
        results.sort(key=lambda x: x["composite_rank"], reverse=True)
        return results[:top_k]


# Singleton instance
semantic_engine = SemanticEngine()
