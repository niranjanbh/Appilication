"""Pre-consultation report service.

Aggregates lab, adherence, wearable data and renders the report HTML.
No PHI is included in log messages — only IDs and aggregate metrics.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import structlog
from html import escape as _esc
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.clinic import Consultation, PreConsultationReport
from app.repositories import pre_consult_reports as reports_repo

logger = structlog.get_logger(__name__)


# ── Data aggregation ──────────────────────────────────────────────────────────


async def build_lab_summary(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
) -> dict[str, Any]:
    """Top 5 biomarkers with most recent value + trend direction, last 90 days."""
    cutoff = datetime.now(UTC) - timedelta(days=90)

    sql = text(
        """
        SELECT
            lower(b->>'name')   AS name,
            b->>'value'         AS value,
            b->>'unit'          AS unit,
            b->>'flag'          AS flag,
            b->>'ref_low'       AS ref_low,
            b->>'ref_high'      AS ref_high,
            r.report_date,
            r.created_at
        FROM kc_lab_reports r
        CROSS JOIN LATERAL jsonb_array_elements(r.parsed_json->'biomarkers') AS b
        WHERE r.patient_id = :patient_id
          AND r.status IN ('ocr_complete', 'patient_review_needed')
          AND r.parsed_json IS NOT NULL
          AND COALESCE(r.report_date::timestamptz, r.created_at) >= :cutoff
        ORDER BY lower(b->>'name'), COALESCE(r.report_date::timestamptz, r.created_at) DESC
        """
    )
    rows = (
        await db.execute(sql, {"patient_id": str(patient_id), "cutoff": cutoff})
    ).mappings().all()

    # Keep only the most recent reading per biomarker name
    seen: set[str] = set()
    top_biomarkers: list[dict[str, Any]] = []
    for row in rows:
        name = row["name"]
        if name in seen:
            continue
        seen.add(name)
        top_biomarkers.append(
            {
                "name": name,
                "value": row["value"],
                "unit": row["unit"],
                "flag": row["flag"],
                "ref_low": row["ref_low"],
                "ref_high": row["ref_high"],
            }
        )
        if len(top_biomarkers) >= 5:
            break

    # Compute trend direction for each (compare to previous reading)
    for bm in top_biomarkers:
        trend = await _get_biomarker_trend(db, patient_id=patient_id, biomarker_name=bm["name"])
        bm["trend"] = trend

    return {"biomarkers": top_biomarkers, "window_days": 90}


async def _get_biomarker_trend(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    biomarker_name: str,
) -> str:
    """Return 'up', 'down', or 'stable' based on last two readings."""
    sql = text(
        """
        SELECT
            b->>'value' AS value,
            COALESCE(r.report_date::timestamptz, r.created_at) AS measured_at
        FROM kc_lab_reports r
        CROSS JOIN LATERAL jsonb_array_elements(r.parsed_json->'biomarkers') AS b
        WHERE r.patient_id = :patient_id
          AND r.status IN ('ocr_complete', 'patient_review_needed')
          AND r.parsed_json IS NOT NULL
          AND lower(b->>'name') = :name
        ORDER BY COALESCE(r.report_date::timestamptz, r.created_at) DESC
        LIMIT 2
        """
    )
    rows = (
        await db.execute(sql, {"patient_id": str(patient_id), "name": biomarker_name})
    ).mappings().all()

    if len(rows) < 2:
        return "stable"
    try:
        current = float(rows[0]["value"])
        previous = float(rows[1]["value"])
    except (TypeError, ValueError):
        return "stable"

    if current > previous * 1.05:
        return "up"
    if current < previous * 0.95:
        return "down"
    return "stable"


async def build_adherence_summary(
    db: AsyncSession,
    *,
    patient_id: uuid.UUID,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Medication compliance rate for the last 30 days from wn_reminder_logs."""
    cutoff = datetime.now(UTC) - timedelta(days=30)

    sql = text(
        """
        SELECT
            COUNT(*) FILTER (WHERE rl.action = 'taken')   AS taken_count,
            COUNT(*) FILTER (WHERE rl.action = 'skipped') AS skipped_count,
            COUNT(*) FILTER (WHERE rl.action = 'snoozed') AS snoozed_count,
            COUNT(*)                                        AS total_count
        FROM wn_reminder_logs rl
        JOIN wn_reminders r ON r.id = rl.reminder_id
        WHERE rl.user_id = :user_id
          AND r.type = 'medication'
          AND rl.scheduled_at >= :cutoff
        """
    )
    row = (
        await db.execute(sql, {"user_id": str(user_id), "cutoff": cutoff})
    ).mappings().first()

    if row is None or (row["total_count"] or 0) == 0:
        return {"compliance_pct": None, "taken": 0, "skipped": 0, "snoozed": 0, "total": 0, "window_days": 30}

    total = row["total_count"] or 0
    taken = row["taken_count"] or 0
    compliance_pct = round((taken / total) * 100, 1) if total > 0 else None

    return {
        "compliance_pct": compliance_pct,
        "taken": taken,
        "skipped": row["skipped_count"] or 0,
        "snoozed": row["snoozed_count"] or 0,
        "total": total,
        "window_days": 30,
    }


async def build_wearable_summary(
    db: AsyncSession,
    *,
    user_id: uuid.UUID,
) -> dict[str, Any]:
    """Average steps, resting HR, sleep duration for the last 30 days."""
    cutoff = datetime.now(UTC) - timedelta(days=30)

    sql = text(
        """
        SELECT
            type,
            AVG((value->>'quantity')::numeric) AS avg_value
        FROM wn_health_datapoints
        WHERE user_id = :user_id
          AND type IN ('steps', 'resting_heart_rate', 'sleep_duration')
          AND measured_at >= :cutoff
        GROUP BY type
        """
    )
    rows = (
        await db.execute(sql, {"user_id": str(user_id), "cutoff": cutoff})
    ).mappings().all()

    summary: dict[str, Any] = {
        "avg_steps": None,
        "avg_resting_hr": None,
        "avg_sleep_hours": None,
        "window_days": 30,
    }
    for row in rows:
        val = float(row["avg_value"]) if row["avg_value"] is not None else None
        if row["type"] == "steps":
            summary["avg_steps"] = round(val) if val is not None else None
        elif row["type"] == "resting_heart_rate":
            summary["avg_resting_hr"] = round(val, 1) if val is not None else None
        elif row["type"] == "sleep_duration":
            # sleep_duration stored in minutes — convert to hours
            summary["avg_sleep_hours"] = round(val / 60, 1) if val is not None else None

    return summary


# ── Orchestration ─────────────────────────────────────────────────────────────


async def generate_report_for_consultation(
    db: AsyncSession,
    *,
    consultation_id: uuid.UUID,
) -> PreConsultationReport | None:
    """Aggregate all data sources and persist the pre-consultation report row.

    Returns None if the consultation is not found or is not in a reportable state.
    No PHI is logged.
    """
    from app.db.enums import ConsultationStatus
    from app.models.clinic import Patient

    log = logger.bind(consultation_id=str(consultation_id))

    result = await db.execute(
        select(Consultation).where(
            Consultation.id == consultation_id,
            Consultation.deleted_at.is_(None),
        )
    )
    consultation = result.scalar_one_or_none()
    if consultation is None:
        log.warning("pre_consult_report.consultation_not_found")
        return None

    if consultation.status not in (ConsultationStatus.SCHEDULED, ConsultationStatus.CONFIRMED):
        log.info(
            "pre_consult_report.skipped_wrong_status",
            status=consultation.status.value,
        )
        return None

    # Resolve patient row and user_id for adherence/wearable queries
    patient_result = await db.execute(
        select(Patient).where(Patient.id == consultation.patient_id)
    )
    patient = patient_result.scalar_one_or_none()
    if patient is None:
        log.warning("pre_consult_report.patient_not_found")
        return None

    log.info("pre_consult_report.aggregating")

    lab_summary = await build_lab_summary(db, patient_id=consultation.patient_id)
    adherence_summary = await build_adherence_summary(
        db, patient_id=consultation.patient_id, user_id=patient.user_id
    )
    wearable_summary = await build_wearable_summary(db, user_id=patient.user_id)

    report = await reports_repo.create_or_update(
        db,
        consultation_id=consultation_id,
        patient_id=consultation.patient_id,
        generated_at=datetime.now(UTC),
        lab_summary=lab_summary,
        adherence_summary=adherence_summary,
        wearable_summary=wearable_summary,
        patient_flags=None,
        intake_responses=None,
    )
    await db.flush()

    log.info("pre_consult_report.generated", report_id=str(report.id))
    return report


# ── HTML rendering ────────────────────────────────────────────────────────────


def render_pre_consult_html(
    *,
    report: PreConsultationReport,
    patient_name: str,
    doctor_name: str,
    scheduled_at: datetime,
) -> str:
    """Render a WeasyPrint-ready HTML string for the pre-consultation report PDF."""
    from datetime import timedelta as _td
    from datetime import timezone

    ist = timezone(_td(hours=5, minutes=30))

    def _fmt(dt: datetime) -> str:
        return dt.astimezone(ist).strftime("%d %b %Y, %I:%M %p IST")

    scheduled_str = _fmt(scheduled_at)
    generated_str = _fmt(report.generated_at)

    lab_rows = ""
    if report.lab_summary and report.lab_summary.get("biomarkers"):
        for bm in report.lab_summary["biomarkers"]:
            trend_symbol = {"up": "↑", "down": "↓", "stable": "↔"}.get(bm.get("trend", "stable"), "↔")
            flag_style = "color:#c0392b;" if bm.get("flag") else ""
            lab_rows += f"""
            <tr>
              <td>{_esc(str(bm.get('name', '')).title())}</td>
              <td style="{flag_style}">{_esc(str(bm.get('value', '—')))} {_esc(str(bm.get('unit', '')))}</td>
              <td>{trend_symbol}</td>
              <td>{_esc(str(bm.get('ref_low', '-')))} - {_esc(str(bm.get('ref_high', '-')))} {_esc(str(bm.get('unit', '')))}</td>
            </tr>"""

    adherence_html = ""
    if report.adherence_summary:
        pct = report.adherence_summary.get("compliance_pct")
        adherence_html = f"""
        <p>Medication adherence (last 30 days):
          <strong>{pct}%</strong> —
          Taken: {report.adherence_summary.get('taken', 0)},
          Skipped: {report.adherence_summary.get('skipped', 0)},
          Snoozed: {report.adherence_summary.get('snoozed', 0)}
        </p>""" if pct is not None else "<p>No medication reminder data available.</p>"

    wearable_html = ""
    if report.wearable_summary:
        ws = report.wearable_summary
        wearable_html = f"""
        <ul>
          <li>Avg daily steps: {ws.get('avg_steps', '—') or '—'}</li>
          <li>Avg resting HR: {ws.get('avg_resting_hr', '—') or '—'} bpm</li>
          <li>Avg sleep: {ws.get('avg_sleep_hours', '—') or '—'} hours</li>
        </ul>"""

    flags_html = ""
    if report.patient_flags:
        flags = report.patient_flags.get("flags", [])
        if flags:
            items = "".join(f"<li>{_esc(str(f))}</li>" for f in flags)
            flags_html = f"<ul>{items}</ul>"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Pre-Consultation Report</title>
  <style>
    body {{ font-family: Arial, sans-serif; font-size: 12px; color: #222; margin: 40px; }}
    h1 {{ font-size: 18px; color: #1a3c5e; border-bottom: 2px solid #1a3c5e; padding-bottom: 6px; }}
    h2 {{ font-size: 14px; color: #1a3c5e; margin-top: 20px; }}
    table {{ border-collapse: collapse; width: 100%; margin-top: 8px; }}
    th {{ background: #1a3c5e; color: white; padding: 6px 8px; text-align: left; }}
    td {{ padding: 5px 8px; border-bottom: 1px solid #e0e0e0; }}
    .meta {{ color: #555; font-size: 11px; }}
    .footer {{ margin-top: 40px; color: #888; font-size: 10px; border-top: 1px solid #ccc; padding-top: 8px; }}
  </style>
</head>
<body>
  <h1>Kyros Clinic — Pre-Consultation Report</h1>
  <p class="meta">
    Patient: <strong>{_esc(patient_name)}</strong> &nbsp;|&nbsp;
    Doctor: <strong>{_esc(doctor_name)}</strong> &nbsp;|&nbsp;
    Consultation: <strong>{scheduled_str}</strong>
  </p>
  <p class="meta">Generated: {generated_str}</p>

  <h2>Lab Summary (last 90 days)</h2>
  {"<table><tr><th>Biomarker</th><th>Latest Value</th><th>Trend</th><th>Reference</th></tr>" + lab_rows + "</table>" if lab_rows else "<p>No lab data available.</p>"}

  <h2>Medication Adherence</h2>
  {adherence_html or "<p>No adherence data available.</p>"}

  <h2>Wearable / Health Summary (last 30 days)</h2>
  {wearable_html or "<p>No wearable data available.</p>"}

  <h2>Patient-Flagged Concerns</h2>
  {flags_html or "<p>No concerns flagged.</p>"}

  <div class="footer">
    Confidential — generated by Kyros Clinic. Report ID: {report.id}
  </div>
</body>
</html>"""
