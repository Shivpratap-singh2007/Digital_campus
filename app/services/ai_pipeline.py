import re
import logging
from typing import Any, Dict, List, Optional, Union
import numpy as np

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger(__name__)

# ==============================================================================
# 1. TEXT CLASSIFICATION & DOMAIN TAGGING (English + Hinglish Support)
# ==============================================================================

CATEGORY_DEFINITIONS = {
    "Sanitation & Plumbing": {
        "phrases": [
            "water cooler", "water leak", "water leaking", "drinking water", "running water",
            "flush not working", "toilet flush", "washroom dirty", "bathroom dirty", "drain blocked",
            "pipe burst", "pipe leak", "sewage leak", "wash basin", "washbasin clogged", "foul smell",
            "bad odor", "terrible smell", "garbage overflow", "dustbin overflow", "pest infestation",
            "paani beh raha", "flush kharab", "nal kharab", "bathroom me paani", "paani nahi aa raha",
            "nal se paani", "ganda paani", "paani ki samasya", "kachra phail gaya", "badboo aa rahi",
            "tank overflow", "water supply", "toilet choke", "drain choked"
        ],
        "keywords": [
            "plumbing", "tap", "leak", "leaking", "pipe", "pipes", "toilet", "toilets", "washroom",
            "washrooms", "restroom", "restrooms", "bathroom", "bathrooms", "flush", "sink", "sinks",
            "basin", "washbasin", "sewage", "drain", "drainage", "clogged", "choked", "stinking",
            "stink", "odor", "stench", "foul", "dirty", "garbage", "trash", "dustbin", "cooler",
            "faucet", "overflow", "geyser", "hygiene", "cockroach", "mosquito", "sewer",
            # Hinglish / Hindi Transliterations
            "paani", "pani", "nal", "nalka", "kachra", "safai", "ganda", "gandi", "badboo",
            "mootri", "peshab", "tonti", "kichad"
        ],
    },
    "Electrical & Hardware": {
        "phrases": [
            "short circuit", "power cut", "power outage", "tube light", "air conditioner",
            "electric shock", "current shock", "wire hanging", "exposed wire", "loose wire",
            "sparking socket", "switch board", "switchboard broken", "fan not working", "light not working",
            "light flickering", "voltage fluctuation", "generator down",
            "bijli chali gayi", "current lag raha", "light nahi chal rahi", "pankha nahi chal raha",
            "spark ho raha", "taar khula", "taar toota", "bijli band", "socket kharab"
        ],
        "keywords": [
            "electrical", "electric", "electricity", "wire", "wires", "wiring", "spark", "sparks",
            "sparking", "shock", "shocks", "socket", "sockets", "switch", "switches", "switchboard",
            "fuse", "fan", "fans", "bulb", "bulbs", "tube", "tubelight", "power", "current",
            "voltage", "mcb", "circuit", "appliance", "plug", "plugs", "tripped", "heater", "ac",
            "generator", "inverter", "earthing", "cables", "motor",
            # Hinglish / Hindi Transliterations
            "bijli", "batti", "taar", "tar", "pankha", "roshni"
        ],
    },
    "Academics & Classroom": {
        "phrases": [
            "lecture hall", "lecture theater", "audio system", "sound system", "podium mic",
            "projector screen", "projector display", "hdmi cable", "smart board", "white board",
            "black board", "attendance portal", "timetable clash", "class schedule", "lab equipment",
            "library book", "student id", "hall ticket", "admit card", "exam hall", "roll number",
            "projector nahi chal raha", "mike kharab", "aawaz nahi aa rahi", "class cancel",
            "exam schedule", "seating arrangement"
        ],
        "keywords": [
            "academic", "academics", "classroom", "classrooms", "lecture", "lectures", "projector",
            "projectors", "mic", "microphone", "speaker", "speakers", "podium", "audio", "sound",
            "blackboard", "whiteboard", "chalk", "marker", "duster", "syllabus", "exam", "exams",
            "examination", "timetable", "schedule", "faculty", "professor", "teacher", "attendance",
            "portal", "library", "assignment", "tutorial", "semester", "grading", "marks",
            # Hinglish / Hindi Transliterations
            "padhai", "class", "sir", "madam", "aawaz", "pariksha"
        ],
    },
    "General Infrastructure": {
        "phrases": [
            "broken glass", "window pane", "door handle", "door lock", "main gate", "elevator stuck",
            "lift not working", "lift stuck", "ceiling plaster", "cracked wall", "broken bench",
            "broken chair", "broken desk", "stair railing", "street light", "campus road",
            "pothole in road", "boundary wall", "sports complex", "gym equipment",
            "darwaza tuta", "khidki tooti", "deewar me crack", "lift kharab", "tala band",
            "tile tooti", "stairs tooti"
        ],
        "keywords": [
            "infrastructure", "building", "door", "doors", "window", "windows", "glass", "gate",
            "gates", "lock", "locks", "key", "keys", "chair", "chairs", "desk", "desks", "bench",
            "benches", "table", "tables", "furniture", "lift", "lifts", "elevator", "elevators",
            "stairs", "staircase", "stairwell", "railing", "wall", "walls", "ceiling", "roof",
            "plaster", "floor", "flooring", "tile", "tiles", "crack", "cracks", "road", "roads",
            "pothole", "pavement", "footpath", "garden", "grounds", "paint", "corridor", "hallway",
            "hostel", "dormitory", "cafeteria", "canteen", "mess", "gym",
            # Hinglish / Hindi Transliterations
            "darwaza", "khidki", "deewar", "chhat", "seedhi", "tala", "toota", "tooti", "futa",
            "tut gaya"
        ],
    },
}


def classify_issue(text: str) -> str:
    """
    Analyzes complaint description and categorizes text into one of:
    - 'Sanitation & Plumbing'
    - 'Electrical & Hardware'
    - 'Academics & Classroom'
    - 'General Infrastructure'
    
    Supports English & Hinglish phrases.
    """
    if not text or not text.strip():
        return "General Infrastructure"

    clean_text = text.lower()
    scores: Dict[str, float] = {cat: 0.0 for cat in CATEGORY_DEFINITIONS}

    for cat, rules in CATEGORY_DEFINITIONS.items():
        # 1. Match multi-word phrases (higher weight)
        for phrase in rules["phrases"]:
            if phrase in clean_text:
                scores[cat] += 3.0

        # 2. Match single keywords with word boundary
        for kw in rules["keywords"]:
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = len(re.findall(pattern, clean_text))
            if matches > 0:
                scores[cat] += matches * 1.0

    # Pick category with highest score
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    best_cat, best_score = sorted_scores[0]

    if best_score > 0:
        return best_cat

    return "General Infrastructure"


# ==============================================================================
# 2. SEVERITY & PRIORITY DETECTION
# ==============================================================================

# Critical hazards trigger P1 immediately
P1_HAZARDS = [
    "fire", "spark", "sparking", "sparks", "shock", "shocks", "electric shock",
    "danger", "dangerous", "smoke", "smoking", "broken glass", "exposed wire",
    "live wire", "open wire", "flame", "flames", "explosion", "gas leak",
    "cylinder leak", "ceiling collapse", "falling plaster", "short circuit",
    "electrocution", "electrocuted", "hazardous", "hazard", "life threatening",
    "heavy flooding", "chemical spill", "toxic",
    # Hinglish / Hindi
    "aag", "aag lag", "current mar raha", "current lag", "dhuan", "khatra",
    "khatarnak", "taar nikal gaya"
]

P2_MEDIUM_KEYWORDS = [
    "leak", "leaking", "overflow", "overflowing", "broken", "urgent", "urgently",
    "clogged", "choked", "blocked", "unusable", "not working", "jammed", "stuck",
    "no water", "no electricity", "power cut", "power outage", "foul smell",
    "blackout", "elevator stuck", "lift stuck", "malfunction", "damaged",
    # Hinglish / Hindi
    "kharab", "paani beh raha", "paani band", "nal tuta", "band hai", "kaam nahi kar raha"
]


def detect_priority(text: str) -> str:
    """
    Detects urgency level returning:
    - 'Critical (P1)' for safety hazards (fire, spark, shock, broken glass, danger, etc.)
    - 'Medium (P2)' for operational disruptions (leak, broken, urgent, etc.)
    - 'Low (P3)' for baseline/routine complaints and suggestions
    """
    if not text or not text.strip():
        return "Low (P3)"

    clean_text = text.lower()

    # 1. Critical safety hazard check (P1)
    for hazard in P1_HAZARDS:
        pattern = r"\b" + re.escape(hazard) + r"\b"
        if re.search(pattern, clean_text):
            return "Critical (P1)"

    # 2. Medium urgency check (P2)
    for med in P2_MEDIUM_KEYWORDS:
        pattern = r"\b" + re.escape(med) + r"\b"
        if re.search(pattern, clean_text):
            return "Medium (P2)"

    # 3. Default normal/low priority (P3)
    return "Low (P3)"


# ==============================================================================
# 3. SEMANTIC SIMILARITY & DUPLICATE GROUPING (TF-IDF + Cosine Similarity)
# ==============================================================================

def _extract_issue_fields(item: Any) -> tuple[int, str, str]:
    """Extracts (id, title, description) from dict or SQLAlchemy model."""
    if isinstance(item, dict):
        return int(item.get("id") or 0), str(item.get("title") or ""), str(item.get("description") or "")
    
    i_id = getattr(item, "id", 0)
    title = getattr(item, "title", "")
    desc = getattr(item, "description", "")
    return int(i_id), str(title), str(desc)


def _stem_text(text: str) -> str:
    """Lightweight, zero-dependency token normalizer and suffix stripper."""
    words = re.findall(r"\b[a-zA-Z0-9_]+\b", text.lower())
    stemmed = [re.sub(r"(ing|ed|es|s)\b", "", w) for w in words]
    return " ".join(stemmed)


def find_duplicate_issues(
    new_title: str,
    new_desc: str,
    existing_issues: Union[List[Any], Any],
    threshold: float = 0.70,
) -> Dict[str, Any]:
    """
    Computes TF-IDF vector representations and cosine similarity against active issues.
    If similarity score > threshold (default 0.70):
    Flags as duplicate candidate with target issue ID.
    
    Returns a dict with:
    - 'is_duplicate': bool
    - 'similarity_score': float (0.0 to 1.0)
    - 'matched_issue_id': int or None
    - 'matched_issue_title': str or None
    - 'duplicates': list of all candidate matches > threshold
    """
    new_text = f"{new_title} {new_desc}".strip()
    
    empty_result = {
        "is_duplicate": False,
        "similarity_score": 0.0,
        "matched_issue_id": None,
        "matched_issue_title": None,
        "duplicates": [],
    }

    if not new_text or not existing_issues:
        return empty_result

    # Format corpus with stemmed text
    corpus = [_stem_text(new_text)]
    metadata = []
    
    for item in existing_issues:
        i_id, title, desc = _extract_issue_fields(item)
        combined = f"{title} {desc}".strip()
        corpus.append(_stem_text(combined))
        metadata.append({"id": i_id, "title": title, "description": desc})

    if not SKLEARN_AVAILABLE:
        # Robust pure-Python token overlap fallback when scikit-learn is not installed
        tokens_new = set(re.findall(r"\w+", new_text.lower()))
        duplicates = []
        for item in existing_issues:
            i_id, title, desc = _extract_issue_fields(item)
            combined = f"{title} {desc}".lower()
            tokens_exist = set(re.findall(r"\w+", combined))
            if not tokens_new or not tokens_exist:
                continue
            intersection = tokens_new.intersection(tokens_exist)
            union = tokens_new.union(tokens_exist)
            score = len(intersection) / len(union) if union else 0.0
            if score >= (threshold * 0.7):
                duplicates.append({
                    "issue_id": i_id,
                    "title": title,
                    "similarity_score": round(score, 4),
                    "is_duplicate_candidate": True,
                })
        duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_match = duplicates[0] if duplicates else None
        return {
            "is_duplicate": top_match is not None,
            "similarity_score": round(top_match["similarity_score"], 4) if top_match else 0.0,
            "matched_issue_id": top_match["issue_id"] if top_match else None,
            "matched_issue_title": top_match["title"] if top_match else None,
            "duplicates": duplicates,
        }

    try:
        vectorizer = TfidfVectorizer(
            stop_words="english",
            lowercase=True,
            ngram_range=(1, 1),
            sublinear_tf=True,
            min_df=1,
        )
        tfidf_matrix = vectorizer.fit_transform(corpus)

        # Compute cosine similarity between new_text (index 0) and all existing issues (indices 1..N)
        cosine_sims = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:]).flatten()

        duplicates = []
        for idx, sim in enumerate(cosine_sims):
            score = float(sim)
            meta = metadata[idx]
            if score >= threshold:
                duplicates.append({
                    "issue_id": meta["id"],
                    "title": meta["title"],
                    "similarity_score": round(score, 4),
                    "is_duplicate_candidate": True,
                })

        duplicates.sort(key=lambda x: x["similarity_score"], reverse=True)
        top_match = duplicates[0] if duplicates else None
        highest_score = float(np.max(cosine_sims)) if len(cosine_sims) > 0 else 0.0

        return {
            "is_duplicate": top_match is not None,
            "similarity_score": round(top_match["similarity_score"], 4) if top_match else round(highest_score, 4),
            "matched_issue_id": top_match["issue_id"] if top_match else None,
            "matched_issue_title": top_match["title"] if top_match else None,
            "duplicates": duplicates,
        }

    except Exception as e:
        logger.warning(f"TF-IDF duplicate detection warning: {e}")
        return empty_result
