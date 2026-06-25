from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "kyros",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)
celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    beat_schedule={
        "generate-pre-consult-reports-tomorrow": {
            "task": "kyrosclinic.comal.generate_pre_consult_reports_for_tomorrow",
            "schedule": crontab(hour=4, minute=0),  # 4 AM UTC ≈ 9:30 AM IST
        },
        "rollup-daily-metrics": {
            "task": "kyros.analytics.rollup_daily",
            "schedule": crontab(hour=2, minute=30),  # 2:30 AM UTC daily
        },
        "publish-cloudwatch-metrics": {
            "task": "kyros.maintenance.publish_metrics",
            "schedule": 60.0,  # every 60 seconds
        },
        "verify-audit-integrity": {
            "task": "kyros.maintenance.verify_audit_integrity",
            "schedule": crontab(hour=1, minute=0),  # 1 AM UTC daily
        },
        "ensure-health-partitions-ahead": {
            "task": "kyros.maintenance.ensure_health_partitions_ahead",
            "schedule": crontab(hour=3, minute=0, day_of_month="1"),  # 1st of each month
        },
        "reconcile-pending-payments": {
            "task": "kyros.payment.reconcile_pending",
            "schedule": crontab(minute=0, hour="*/2"),  # every 2 hours
        },
        "provision-upcoming-video-rooms": {
            "task": "kyros.video.provision_upcoming_rooms",
            "schedule": crontab(minute="*/1"),  # every minute
        },
        "dispatch-due-reminders": {
            "task": "kyros.reminder.dispatch_due",
            "schedule": crontab(minute="*/5"),  # every 5 minutes
        },
        "mark-auto-no-show": {
            "task": "kyros.consultation.mark_auto_no_show",
            "schedule": crontab(minute="*/15"),  # every 15 minutes
        },
    },
)
celery_app.autodiscover_tasks([
    "app.tasks.notification_tasks",
    "app.tasks.ocr_tasks",
    "app.tasks.payment_tasks",
    "app.tasks.prescription_tasks",
    "app.tasks.reminder_tasks",
    "app.tasks.video_tasks",
    "app.tasks.data_subject_request",
    "app.tasks.maintenance_tasks",
    "app.tasks.report_tasks",
    "app.tasks.analytics_tasks",
    "app.tasks.doctor_tasks",
    "app.tasks.consultation_tasks",
])
