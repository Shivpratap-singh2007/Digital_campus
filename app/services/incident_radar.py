import hashlib
import json
import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import or_

from app.extensions import db
from app.models.complaint import Complaint
from app.models.radar import (
    InfrastructureDependency,
    DependencyLocation,
    RadarSuggestion,
    RadarSuggestionReport,
)
from app.services.semantic import semantic_engine

logger = logging.getLogger(__name__)

# Configurable Radar Analysis Parameters
RADAR_LOOKBACK_HOURS = 48  # Active lookback window for reports
RADAR_CORRELATION_WINDOW_HOURS = 4  # Time clustering window between correlated reports
RADAR_MAX_CANDIDATES = 60  # Bounded processing limit per run
RADAR_VERSION = "radar_v1.0"

# Explicit Versioned Symptom Dictionaries & Compatibility Mappings
SYMPTOM_PROTOTYPES = {
    "electrical_power_loss": [
        "power cut", "power outage", "no power", "blackout", "stopped working",
        "power off", "electricity gone", "no electricity", "tripped", "not turning on",
        "shut down", "dark", "no current", "meter off", "fuse blown", "no supply",
        "lost power", "bijli chali gayi", "power nahi", "spark", "current lag"
    ],
    "water_supply_disruption": [
        "no water", "water cut", "water stopped", "low pressure", "dry tap",
        "tank empty", "water supply off", "paani band", "paani nahi aa raha",
        "no running water", "supply stopped", "pipe burst", "leak"
    ],
    "network_outage": [
        "no internet", "wifi down", "network disconnected", "no connection",
        "router off", "switch down", "lan dead", "internet nahi",
        "wifi nahi chal raha", "offline", "server down"
    ],
}

DEPENDENCY_SYMPTOM_COMPATIBILITY = {
    "electrical_supply": ["electrical_power_loss"],
    "water_supply": ["water_supply_disruption"],
    "network": ["network_outage"],
}


def extract_report_symptom(title: str, description: str) -> Optional[str]:
    """
    Identifies reported symptom / service disruption using explicit versioned prototypes.
    Returns symptom key (e.g. 'electrical_power_loss') or None if no compatible disruption matched.
    """
    combined = f"{title} {description}".lower()
    for symptom_key, triggers in SYMPTOM_PROTOTYPES.items():
        for trigger in triggers:
            if trigger in combined:
                return symptom_key
    return None


def calculate_fingerprint(report_ids: List[int], suggestion_type: str, dependency_id: Optional[int]) -> str:
    """Generates deterministic SHA-256 fingerprint for a specific set of evidence."""
    sorted_ids = sorted(report_ids)
    raw = f"{suggestion_type}:{dependency_id or 'none'}:{','.join(map(str, sorted_ids))}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def match_complaint_to_dependency_location(
    complaint: Complaint, locations: List[DependencyLocation]
) -> Optional[DependencyLocation]:
    """
    Conservatively checks if complaint building, room, or title matches a known mapped location.
    Does NOT guess or assign vague reports to exact assets.
    """
    c_room = (complaint.room or "").strip().lower()
    c_desc = f"{complaint.title} {complaint.description}".lower()

    for loc in locations:
        loc_room = (loc.room or "").strip().lower()
        loc_name = loc.location_name.strip().lower()

        # Exact room match
        if c_room and loc_room and (c_room == loc_room or loc_room in c_room or c_room in loc_room):
            return loc

        # Specific location name match in description or title
        if loc_name and loc_name in c_desc:
            return loc

    return None


def run_incident_radar_analysis() -> Dict[str, Any]:
    """
    Executes bounded, explainable incident correlation across recent active complaints.
    
    Advisory Principles:
    - Evidence-based correlation, not confirmed root cause.
    - Preserves existing human review decisions on reruns.
    - Distinguishes Type 1 (Possible shared-dependency) from Type 2 (Location/time cluster).
    - Submitter identities strictly omitted.
    """
    now = datetime.now(timezone.utc)
    lookback_cutoff = now - timedelta(hours=RADAR_LOOKBACK_HOURS)

    # 1. Fetch eligible active complaints (bounded lookback, exclude resolved)
    eligible_complaints = (
        Complaint.query.filter(
            Complaint.status.notin_(["resolved", "cancelled"]),
            Complaint.created_at >= lookback_cutoff,
        )
        .order_by(Complaint.created_at.desc())
        .limit(RADAR_MAX_CANDIDATES)
        .all()
    )

    if not eligible_complaints:
        return {
            "scanned_reports_count": 0,
            "created_suggestions_count": 0,
            "preserved_suggestions_count": 0,
            "suggestions": [],
            "analysis_version": RADAR_VERSION,
        }

    # 2. Group eligible complaints by building
    by_building: Dict[str, List[Complaint]] = {}
    for comp in eligible_complaints:
        bldg = comp.building.strip()
        by_building.setdefault(bldg, []).append(comp)

    # 3. Fetch all configured infrastructure dependencies
    all_dependencies = InfrastructureDependency.query.all()
    deps_by_building: Dict[str, List[InfrastructureDependency]] = {}
    for dep in all_dependencies:
        deps_by_building.setdefault(dep.building.strip(), []).append(dep)

    created_count = 0
    preserved_count = 0
    generated_suggestions: List[RadarSuggestion] = []

    is_semantic_active = getattr(semantic_engine, "is_available", False)
    analysis_method = "hybrid_embedding_symptom_v1" if is_semantic_active else "rule_based_symptom_v1"

    # 4. Analyze each building's reports
    for bldg, complaints in by_building.items():
        if len(complaints) < 2:
            continue

        bldg_deps = deps_by_building.get(bldg, [])
        processed_complaint_ids = set()

        # --- A. Check Configured Shared Dependencies (Type 1) ---
        for dep in bldg_deps:
            compatible_symptoms = DEPENDENCY_SYMPTOM_COMPATIBILITY.get(dep.dependency_type, [])
            matched_reports: List[Tuple[Complaint, DependencyLocation, str]] = []

            for comp in complaints:
                symptom = extract_report_symptom(comp.title, comp.description)
                if not symptom or symptom not in compatible_symptoms:
                    continue

                matched_loc = match_complaint_to_dependency_location(comp, dep.locations)
                if matched_loc:
                    matched_reports.append((comp, matched_loc, symptom))

            # Need at least 2 distinct reports sharing this dependency within time window
            if len(matched_reports) >= 2:
                # Check temporal proximity (max gap between earliest and latest within window)
                matched_reports.sort(key=lambda x: x[0].created_at)
                first_ts = matched_reports[0][0].created_at
                last_ts = matched_reports[-1][0].created_at
                time_span_hours = (last_ts - first_ts).total_seconds() / 3600.0

                if time_span_hours <= RADAR_CORRELATION_WINDOW_HOURS * 2:  # Bounded cluster
                    report_ids = [m[0].id for m in matched_reports]
                    fingerprint = calculate_fingerprint(report_ids, "shared_dependency", dep.id)

                    existing = RadarSuggestion.query.filter_by(fingerprint=fingerprint).first()
                    if existing:
                        preserved_count += 1
                        generated_suggestions.append(existing)
                        for r_id in report_ids:
                            processed_complaint_ids.add(r_id)
                        continue

                    # Create evidence record
                    evidence = {
                        "report_ids": report_ids,
                        "time_window_start": first_ts.isoformat(),
                        "time_window_end": last_ts.isoformat(),
                        "time_span_hours": round(time_span_hours, 2),
                        "time_basis": "submission_time",
                        "time_basis_note": "Using report submission timestamp as proxy for incident timing.",
                        "location_evidence": {
                            "building": bldg,
                            "matched_locations": [
                                {
                                    "report_id": m[0].id,
                                    "room": m[0].room or m[1].room,
                                    "location_name": m[1].location_name,
                                    "asset_name": m[1].asset_name,
                                }
                                for m in matched_reports
                            ],
                        },
                        "dependency_identifier": dep.dependency_identifier,
                        "dependency_name": dep.name,
                        "dependency_type": dep.dependency_type,
                        "is_synthetic_dependency": dep.is_synthetic,
                        "symptoms_detected": {
                            str(m[0].id): m[2] for m in matched_reports
                        },
                        "missing_information": [
                            "No real-time branch circuit IoT telemetry connected.",
                            "Asset-level power metering not verified automatically.",
                            "Physical inspection required to confirm upstream breaker status.",
                        ],
                        "suggestion_reasons": [
                            f"{len(matched_reports)} reports occurred within {round(time_span_hours, 1)} hours of each other.",
                            f"Locations share verified infrastructure dependency '{dep.name}' ({dep.dependency_identifier}).",
                            f"Reported disruptions ({', '.join(set(m[2] for m in matched_reports))}) are physically compatible with {dep.dependency_type}.",
                        ],
                        "analysis_method": analysis_method,
                        "is_semantic_available": is_semantic_active,
                        "evidence_level": "Supported by Configured Infrastructure Dependency",
                        "warning": "Suggested connection, not a confirmed cause. Human operational review required before coordinating response.",
                    }

                    loc_names = ", ".join(list(dict.fromkeys(m[1].location_name for m in matched_reports)))
                    headline = f"Possible shared-dependency incident: {dep.name}"
                    summary = (
                        f"{len(matched_reports)} reports across {loc_names} in {bldg} "
                        f"occurred within a {round(time_span_hours, 1)}-hour window. These locations share "
                        f"configured supply dependency '{dep.name}' with compatible reported symptoms."
                    )

                    sugg = RadarSuggestion(
                        suggestion_type="shared_dependency",
                        status="pending_review",
                        building=bldg,
                        dependency_id=dep.id,
                        headline=headline,
                        summary=summary,
                        fingerprint=fingerprint,
                        evidence_json=json.dumps(evidence),
                        analysis_version=RADAR_VERSION,
                    )
                    db.session.add(sugg)
                    db.session.flush()

                    for m in matched_reports:
                        assoc = RadarSuggestionReport(
                            suggestion_id=sugg.id,
                            complaint_id=m[0].id,
                            detected_symptom=m[2],
                            matched_asset_name=m[1].asset_name,
                        )
                        db.session.add(assoc)
                        processed_complaint_ids.add(m[0].id)

                    created_count += 1
                    generated_suggestions.append(sugg)

        # --- B. Check Location/Time Clusters Without Configured Dependency (Type 2) ---
        remaining_complaints = [c for c in complaints if c.id not in processed_complaint_ids]
        if len(remaining_complaints) >= 2:
            remaining_complaints.sort(key=lambda x: x.created_at)
            first_ts = remaining_complaints[0].created_at
            last_ts = remaining_complaints[-1].created_at
            time_span_hours = (last_ts - first_ts).total_seconds() / 3600.0

            if time_span_hours <= RADAR_CORRELATION_WINDOW_HOURS:
                cluster_reports = remaining_complaints[:4]  # Bounded cluster
                report_ids = [c.id for c in cluster_reports]
                fingerprint = calculate_fingerprint(report_ids, "location_time_cluster", None)

                existing = RadarSuggestion.query.filter_by(fingerprint=fingerprint).first()
                if existing:
                    preserved_count += 1
                    generated_suggestions.append(existing)
                else:
                    evidence = {
                        "report_ids": report_ids,
                        "time_window_start": first_ts.isoformat(),
                        "time_window_end": last_ts.isoformat(),
                        "time_span_hours": round(time_span_hours, 2),
                        "time_basis": "submission_time",
                        "time_basis_note": "Using report submission timestamp as proxy for incident timing.",
                        "location_evidence": {
                            "building": bldg,
                            "rooms": [c.room for c in cluster_reports if c.room],
                        },
                        "dependency_identifier": None,
                        "dependency_name": None,
                        "dependency_type": None,
                        "symptoms_detected": {
                            str(c.id): extract_report_symptom(c.title, c.description) or "unclassified_disruption"
                            for c in cluster_reports
                        },
                        "missing_information": [
                            "No configured shared infrastructure dependency in this facility sector.",
                            "Unknown whether these disruptions share an operational connection.",
                        ],
                        "suggestion_reasons": [
                            f"{len(cluster_reports)} disruptions reported in {bldg} within {round(time_span_hours, 1)} hours.",
                            "Temporal and spatial proximity detected, but infrastructure relationship is unknown.",
                        ],
                        "analysis_method": analysis_method,
                        "is_semantic_available": is_semantic_active,
                        "evidence_level": "Location/Time Cluster Only (No Dependency Established)",
                        "warning": "Multiple disruptions reported in this area. Cause unknown. Human review recommended.",
                    }

                    headline = f"Location/Time Cluster: {bldg}"
                    summary = (
                        f"Multiple disruptions ({len(cluster_reports)} reports) reported in {bldg} "
                        f"within a {round(time_span_hours, 1)}-hour window. No configured shared infrastructure "
                        f"dependency established. Cause unknown; human review recommended."
                    )

                    sugg = RadarSuggestion(
                        suggestion_type="location_time_cluster",
                        status="pending_review",
                        building=bldg,
                        dependency_id=None,
                        headline=headline,
                        summary=summary,
                        fingerprint=fingerprint,
                        evidence_json=json.dumps(evidence),
                        analysis_version=RADAR_VERSION,
                    )
                    db.session.add(sugg)
                    db.session.flush()

                    for c in cluster_reports:
                        assoc = RadarSuggestionReport(
                            suggestion_id=sugg.id,
                            complaint_id=c.id,
                            detected_symptom=extract_report_symptom(c.title, c.description),
                        )
                        db.session.add(assoc)

                    created_count += 1
                    generated_suggestions.append(sugg)

    db.session.commit()

    return {
        "scanned_reports_count": len(eligible_complaints),
        "created_suggestions_count": created_count,
        "preserved_suggestions_count": preserved_count,
        "analysis_version": RADAR_VERSION,
    }


def seed_synthetic_radar_demo() -> Dict[str, Any]:
    """
    Explicit idempotent seeder for synthetic demo infrastructure dependencies (Scenario A).
    Never fabricates mappings during normal inference.
    """
    dep_id = "ELEC-PANEL-B1-P1"
    existing_dep = InfrastructureDependency.query.filter_by(dependency_identifier=dep_id).first()

    if not existing_dep:
        dep = InfrastructureDependency(
            dependency_identifier=dep_id,
            name="Block B Electrical Sub-Distribution Board P1",
            dependency_type="electrical_supply",
            building="Academic Block B",
            description="Synthetic demo electrical panel supplying Computer Lab, Room 102, and Corridor B1.",
            is_synthetic=True,
        )
        db.session.add(dep)
        db.session.flush()

        locations = [
            DependencyLocation(
                dependency_id=dep.id,
                location_name="Computer Lab",
                room="Lab 101",
                asset_name="Workstation Circuit Feed",
                is_synthetic=True,
            ),
            DependencyLocation(
                dependency_id=dep.id,
                location_name="Classroom 102",
                room="102",
                asset_name="Projector & Podium Circuit Feed",
                is_synthetic=True,
            ),
            DependencyLocation(
                dependency_id=dep.id,
                location_name="Water Dispenser Area",
                room="Corridor B1",
                asset_name="Dispenser Chiller Power Feed",
                is_synthetic=True,
            ),
        ]
        db.session.add_all(locations)
        db.session.commit()
        return {
            "status": "created",
            "dependency": dep.dependency_identifier,
            "locations_count": len(locations),
        }

    return {
        "status": "preserved",
        "dependency": existing_dep.dependency_identifier,
        "locations_count": len(existing_dep.locations),
    }

