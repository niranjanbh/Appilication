"""Server-authoritative consultation pricing.

The fee is NEVER accepted from the client — it is resolved here from config so a
patient cannot influence what they are charged. This is the minimal, correct
pricing source; richer per-vertical pricing and coupon handling arrive with the
admin pricing-as-config work (later P-prompt).
"""

from __future__ import annotations

from app.core.config import settings
from app.db.enums import ConsultationType


def get_consultation_fee_paise(consultation_type: ConsultationType) -> int:
    """Return the authoritative consultation fee in paise for the given type."""
    if consultation_type == ConsultationType.FOLLOW_UP:
        return settings.consultation_fee_followup_paise
    return settings.consultation_fee_initial_paise
