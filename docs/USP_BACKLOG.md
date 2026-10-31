# CampusVoice: USP Backlog & Future Roadmap

> [!IMPORTANT]
> The features detailed in this document are **EXPLICITLY NOT IMPLEMENTED** in the current release.
> The current system focuses strictly on stabilizing and proving the **Original Problem Statement (R1 - R9)** end-to-end.
> These proposals represent candidate innovations for post-baseline development.

---

## 1. USP 1: AI Complaint Interviewer

- **Status:** `NOT IMPLEMENTED / CANDIDATE FOR FUTURE SPRINT`
- **Concept:** A conversational intake assistant that dynamically interviews the student during submission to gather missing operational details before form completion.

### Proposed Capabilities
1. **Dynamic Clarification:** If a student types "the lift is broken", the agent prompts: *"Which wing or floor is the elevator currently stuck on?"*
2. **Multi-turn Transcript Attachment:** Attaches the structured Q&A transcript to the complaint record as supplementary context.
3. **Draft Synthesis:** Automatically extracts location, symptom, urgency, and category into the standard complaint fields once clarified.

### Architectural Prerequisites Before Implementation
- Async LLM integration with strict latency budgets (<1.5s streaming).
- Structured JSON output parsing with schema enforcement.
- Strict anti-hallucination guardrails preventing false promises to students regarding repair timelines.
- Fallback button enabling traditional static form entry at any point.

---

## 2. USP 2: Admin Evidence Copilot

- **Status:** `NOT IMPLEMENTED / CANDIDATE FOR FUTURE SPRINT`
- **Concept:** An operational decision-support copilot for campus maintenance directors to synthesize multi-report evidence bundles.

### Proposed Capabilities
1. **Visual Cross-Referencing:** Multimodal image comparison to verify if two uploaded photos show the same physical damage from different angles.
2. **Resolution Synthesis:** Generates draft resolution summaries by comparing before-and-after maintenance photos.
3. **Dispute Root-Cause Summary:** Summarizes why submitters marked a resolution as `not_fixed` or `partially_fixed`.

### Architectural Prerequisites Before Implementation
- Multimodal vision model support (e.g. Gemini API / Vision endpoint).
- Data residency compliance ensuring student photos are processed in accordance with campus privacy policies.
- Handler-in-the-loop requirement: Copilot suggestions must remain draft proposals and cannot auto-close or alter database status without explicit human approval.

---

## 3. Prioritized Implementation Sequence

1. **Phase 1 (CURRENT - COMPLETED):** Original Problem Statement baseline (R1 to R9) complete, tested, and stabilized.
2. **Phase 2 (Candidate):** AI Complaint Interviewer prototype on `/complaints/new/interactive`.
3. **Phase 3 (Candidate):** Admin Evidence Copilot on `/issues/:id/evidence`.

