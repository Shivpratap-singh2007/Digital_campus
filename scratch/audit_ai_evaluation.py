import sys
import os
sys.path.insert(0, os.path.abspath("."))

from app import create_app
from app.services.semantic import semantic_engine
from app.services.priority_rules import evaluate_priority

app = create_app()

examples = [
    ("Wi-Fi failure", "Hostel Wi-Fi is completely down since morning and students cannot access online study material.", "IT/connectivity", "complaint"),
    ("Sanitation problem", "Washrooms on 3rd floor are extremely dirty, taps leaking, and bad smell in the corridor.", "Sanitation", "complaint"),
    ("Water/electrical infrastructure", "Drinking water cooler has water pooling under it and the electrical cable is frayed.", "Infrastructure", "complaint"),
    ("Academic issue", "Microphone in Lecture Hall 201 is producing loud feedback screeching during lectures.", "Academics", "complaint"),
    ("Student service issue", "Mess food quality in cafeteria is stale and unhygienic with cold meals being served.", "Student services", "complaint"),
    ("Ambiguous short text", "Fix this please.", "Not sure", "complaint"),
    ("Same-incident paraphrase A", "Sparking electrical outlet near workstation 4 in Lab 301.", "Infrastructure", "complaint"),
    ("Same-incident paraphrase B", "Wall socket emitting sparks and smoke in Lab 301 Science Block.", "Infrastructure", "complaint"),
    ("Similar wording, different room", "Sparking electrical outlet in Room 102 Library.", "Infrastructure", "complaint"),
    ("Active hazard", "Exposed live wire hanging low near staircase with active sparks.", "Infrastructure", "complaint"),
    ("Negated/historical hazard", "Exposed wire in corridor was repaired last week and is no longer sparking.", "Infrastructure", "complaint"),
    ("Suggestion", "Request to install more recycling bins and outdoor benches near the main sports ground.", "Other", "suggestion"),
]

print("=== ACTUAL AI AUDIT: SEMANTIC & RULE EVALUATION ===")
with app.app_context():
    print(f"Model loaded: {semantic_engine.is_available}")
    print(f"Load error: {semantic_engine.load_error}")
    print(f"Model object: {type(semantic_engine._model)}")
    print(f"Precomputed categories: {list(semantic_engine._category_embeddings.keys())}\n")

    for label, text, user_cat, sub_type in examples:
        print(f"--- Example: [{label}] ---")
        print(f"Text: \"{text}\"")
        
        # 1. Semantic Categorization
        cat_res = semantic_engine.suggest_category(text, user_cat)
        print(f"  [Semantic AI] Suggested Category: '{cat_res['suggested_category']}'")
        print(f"  [Semantic AI] Cosine Similarity: {cat_res['similarity']:.4f}")
        print(f"  [Semantic AI] Reason: {cat_res['reason']}")
        print(f"  [Semantic AI] Is Ambiguous: {cat_res['is_ambiguous']}")
        print(f"  [Semantic AI] Is Available: {cat_res['is_available']}")
        
        # 2. Priority Rules
        prio_res = evaluate_priority(text, sub_type)
        print(f"  [Priority Rules] Suggested Priority: '{prio_res.suggested_priority}'")
        print(f"  [Priority Rules] Matched Phrase: '{prio_res.matched_phrase}'")
        print(f"  [Priority Rules] Explanation: {prio_res.explanation}")
        print(f"  [Priority Rules] Ambiguous Flag: {prio_res.is_ambiguous}")
        print()

    # Embedding and cosine similarity comparison between Paraphrase A, B, and Different Room
    print("--- Similarity Comparison Matrix ---")
    emb_a = semantic_engine.encode_text(examples[6][1]) # Paraphrase A
    emb_b = semantic_engine.encode_text(examples[7][1]) # Paraphrase B
    emb_diff = semantic_engine.encode_text(examples[8][1]) # Different room

    import numpy as np
    sim_ab = np.dot(emb_a, emb_b)
    sim_a_diff = np.dot(emb_a, emb_diff)
    sim_b_diff = np.dot(emb_b, emb_diff)

    print(f"Cosine Similarity (Paraphrase A <-> Paraphrase B, same location): {sim_ab:.4f}")
    print(f"Cosine Similarity (Paraphrase A <-> Different Room): {sim_a_diff:.4f}")
    print(f"Cosine Similarity (Paraphrase B <-> Different Room): {sim_b_diff:.4f}")

