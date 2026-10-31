import sys
import os
import json
sys.path.insert(0, os.path.abspath("."))

from app import create_app
from app.services.semantic import semantic_engine
from app.services.priority_rules import evaluate_priority
import numpy as np

app = create_app()

test_cases = [
    # English cases
    {"id": "EN-1", "lang": "English", "expected_cat": "IT/connectivity", "text": "Hostel Wi-Fi is completely down since morning and students cannot access online study material.", "sub_type": "complaint"},
    {"id": "EN-2", "lang": "English", "expected_cat": "Sanitation", "text": "Washrooms on 3rd floor are extremely dirty, taps leaking, and bad smell in the corridor.", "sub_type": "complaint"},
    {"id": "EN-3", "lang": "English", "expected_cat": "Infrastructure", "text": "Wall socket near bench 4 is actively sparking and emitting a burning smell. Immediate fire hazard.", "sub_type": "complaint"},
    {"id": "EN-4", "lang": "English", "expected_cat": "Academics", "text": "Projector in Lecture Hall 101 is flickering and presentation slides are unreadable during classes.", "sub_type": "complaint"},
    {"id": "EN-5", "lang": "English", "expected_cat": "Student services", "text": "Hostel mess dinner is exhausting before 9 PM leaving students hungry.", "sub_type": "complaint"},
    {"id": "EN-6", "lang": "English", "expected_cat": "Other", "text": "Request to install 24/7 automated book drop box outside the library entrance.", "sub_type": "suggestion"},
    # Hindi cases (Devanagari)
    {"id": "HI-1", "lang": "Hindi", "expected_cat": "Sanitation", "text": "तीसरी मंजिल के शौचालय में पानी की पाइप लीक हो रही है और बहुत बदबू आ रही है।", "sub_type": "complaint"},
    {"id": "HI-2", "lang": "Hindi", "expected_cat": "IT/connectivity", "text": "लाइब्रेरी में वाई-फाई बिल्कुल नहीं चल रहा है, इंटरनेट कनेक्शन बार-बार कट रहा है।", "sub_type": "complaint"},
    {"id": "HI-3", "lang": "Hindi", "expected_cat": "Infrastructure", "text": "कंप्यूटर लैब में बिजली का खुला तार लटक रहा है जिससे चिंगारी निकल रही है।", "sub_type": "complaint"},
    {"id": "HI-4", "lang": "Hindi", "expected_cat": "Student services", "text": "हॉस्टल मेस में खाना बहुत ठंडा और बासी मिल रहा है।", "sub_type": "complaint"},
    # Hinglish cases (Roman script)
    {"id": "HIN-1", "lang": "Hinglish", "expected_cat": "Sanitation", "text": "3rd floor washroom me paani tapak raha hai aur bahut gandagi hai.", "sub_type": "complaint"},
    {"id": "HIN-2", "lang": "Hinglish", "expected_cat": "IT/connectivity", "text": "Hostel me wifi connect nahi ho raha subah se, speed bilkul slow hai.", "sub_type": "complaint"},
    {"id": "HIN-3", "lang": "Hinglish", "expected_cat": "Infrastructure", "text": "Lab 102 me switch board se spark nikal raha hai, dangerous live wire hai.", "sub_type": "complaint"},
    {"id": "HIN-4", "lang": "Hinglish", "expected_cat": "Academics", "text": "LH 201 ka projector display baar baar band ho raha hai class ke beech me.", "sub_type": "complaint"},
    # Negations & Historical Edge Cases
    {"id": "NEG-1", "lang": "English", "expected_cat": "Infrastructure", "text": "Electrician inspected the socket, there is no exposed wire found.", "sub_type": "complaint"},
    {"id": "HIST-1", "lang": "English", "expected_cat": "Infrastructure", "text": "The sparking cable was already repaired yesterday by maintenance staff.", "sub_type": "complaint"},
    {"id": "AMB-1", "lang": "English", "expected_cat": "Not sure", "text": "Please fix this immediately.", "sub_type": "complaint"},
]

results = []

with app.app_context():
    print(f"Model loaded: {semantic_engine.is_available}")
    print(f"Model Name: paraphrase-multilingual-MiniLM-L12-v2")
    
    for case in test_cases:
        text = case["text"]
        cat_res = semantic_engine.suggest_category(text, "Not sure")
        prio_res = evaluate_priority(text, case["sub_type"])
        
        entry = {
            "id": case["id"],
            "lang": case["lang"],
            "text": text,
            "expected_cat": case["expected_cat"],
            "suggested_cat": cat_res["suggested_category"],
            "similarity": round(cat_res["similarity"], 4) if cat_res["similarity"] is not None else None,
            "is_ambiguous": cat_res["is_ambiguous"],
            "reason": cat_res["reason"],
            "priority": prio_res.suggested_priority,
            "matched_phrase": prio_res.matched_phrase,
            "priority_explanation": prio_res.explanation,
            "priority_ambiguous": prio_res.is_ambiguous,
            "cat_match": cat_res["suggested_category"] == case["expected_cat"] if case["expected_cat"] != "Not sure" else None
        }
        results.append(entry)
        print(f"[{case['id']}] Lang: {case['lang']:8s} | Expected: {case['expected_cat']:16s} | Got: {str(cat_res['suggested_category']):16s} | Sim: {entry['similarity']} | Amb: {entry['is_ambiguous']} | Pri: {entry['priority']}")

    # Paraphrase and clustering analysis
    p1 = "Sparking electrical outlet near workstation 4 in Lab 301."
    p2 = "Wall socket emitting sparks and smoke in Lab 301 Science Block."
    p_diff = "Sparking electrical outlet in Room 102 Library."
    p_other = "Cafeteria food quality is poor."

    e1 = semantic_engine.encode_text(p1)
    e2 = semantic_engine.encode_text(p2)
    e_diff = semantic_engine.encode_text(p_diff)
    e_other = semantic_engine.encode_text(p_other)

    sim_12 = float(np.dot(e1, e2))
    sim_1_diff = float(np.dot(e1, e_diff))
    sim_1_other = float(np.dot(e1, e_other))

    print("\n--- Clustering & Relatedness ---")
    print(f"Same issue paraphrase similarity: {sim_12:.4f}")
    print(f"Different location same issue similarity: {sim_1_diff:.4f}")
    print(f"Unrelated category similarity: {sim_1_other:.4f}")

    with open("scratch/ai_eval_results.json", "w", encoding="utf-8") as f:
        json.dump({
            "cases": results,
            "clustering": {
                "same_issue_paraphrase": round(sim_12, 4),
                "different_location_same_issue": round(sim_1_diff, 4),
                "unrelated_category": round(sim_1_other, 4)
            }
        }, f, indent=2, ensure_ascii=False)

