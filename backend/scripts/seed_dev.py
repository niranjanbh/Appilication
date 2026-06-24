"""Development seed script — idempotent fixture loader.

Creates demo doctors, a coordinator, and demo patients.
Safe to run multiple times: each entity is upserted by its natural key
(phone number for users, NMC number for doctors).

Usage:
    python scripts/seed_dev.py          # from backend/
    make seed                           # via Makefile
"""

from __future__ import annotations

import asyncio
import os
import sys
from datetime import UTC, datetime

# Ensure the project root is on sys.path so `import app` works when the script
# is invoked directly via `python scripts/seed_dev.py` (not via `python -m`).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def main(hash_password=None) -> None:
    import os

    os.environ.setdefault(
        "KYROS_DATABASE_URL",
        "postgresql+asyncpg://kyros:kyros@localhost:5432/kyros",
    )
    os.environ.setdefault(
        "KYROS_JWT_SECRET",
        "dev_jwt_secret_minimum_32_characters_long_xxxx",
    )
    os.environ.setdefault(
        "KYROS_OTP_SECRET",
        "dev_otp_secret_minimum_32_characters_long_yyyy",
    )

    from sqlalchemy import select, text

    from app.core.security import hash_password
    from app.db.enums import CoordinatorStatus, CredentialType, DoctorStatus, UserRole
    from app.db.session import AsyncSessionLocal
    from app.models.admin import Coordinator
    from app.models.clinic import Patient
    from app.models.doctor import Credential, Doctor
    from app.models.identity import User

    async with AsyncSessionLocal() as db:
        # ── Demo doctors ───────────────────────────────────────────────────────

        doctors_seed = [
            {
                "name": "Dr. Meera Iyer",
                "email": "dr.meera@dev.kyros.local",
                "phone": "+919800000001",
                "nmc": "NMC-2015-12345",
                "state_council": "Karnataka Medical Council",
                "specialty": ["endocrinologist"],
                "conditions": ["thyroid", "pcos", "hormones_trt"],
                "languages": ["en", "hi", "kn"],
                "status": DoctorStatus.ACTIVE,
                "bio_short": "Endocrinologist with 10+ years in thyroid and hormonal health.",
                "bio_long": (
                    "Dr. Meera Iyer is a specialist in endocrinology based in Bengaluru. "
                    "She has treated over 3,000 patients with thyroid disorders, PCOS, and "
                    "hormonal imbalances. She completed her MD in Internal Medicine from "
                    "JIPMER, Puducherry and her DM in Endocrinology from AIIMS Delhi."
                ),
                "photo_url": None,
                "revenue_share_pct": "50.00",
                "credentials": [
                    {"type": CredentialType.MBBS, "institution": "JIPMER, Puducherry", "year": 2009},
                    {"type": CredentialType.MD, "institution": "JIPMER, Puducherry", "year": 2012},
                    {"type": CredentialType.DM, "institution": "AIIMS Delhi", "year": 2015},
                ],
            },
            {
                "name": "Dr. Arjun Sharma",
                "email": "dr.arjun@dev.kyros.local",
                "phone": "+919800000002",
                "nmc": "NMC-2012-67890",
                "state_council": "Delhi Medical Council",
                "specialty": ["general_medicine", "lifestyle_medicine"],
                "conditions": ["weight", "longevity"],
                "languages": ["en", "hi"],
                "status": DoctorStatus.ACTIVE,
                "bio_short": "Internist specialising in weight management and healthy ageing.",
                "bio_long": (
                    "Dr. Arjun Sharma practises evidence-based lifestyle medicine in Delhi. "
                    "He integrates metabolic health, nutritional science, and behavioural "
                    "change to help patients achieve sustainable weight loss and longevity. "
                    "He completed his MBBS and MD from Maulana Azad Medical College."
                ),
                "photo_url": None,
                "revenue_share_pct": "50.00",
                "credentials": [
                    {"type": CredentialType.MBBS, "institution": "Maulana Azad Medical College", "year": 2006},
                    {"type": CredentialType.MD, "institution": "Maulana Azad Medical College", "year": 2010},
                    {
                        "type": CredentialType.FELLOWSHIP,
                        "institution": "American College of Lifestyle Medicine",
                        "year": 2014,
                    },
                ],
            },
            {
                "name": "Dr. Priya Nair",
                "email": "dr.priya@dev.kyros.local",
                "phone": "+919800000003",
                "nmc": "NMC-2018-11111",
                "state_council": "Maharashtra Medical Council",
                "specialty": ["dermatologist"],
                "conditions": ["skin_hair"],
                "languages": ["en", "hi", "ml"],
                "status": DoctorStatus.ACTIVE,
                "bio_short": "Dermatologist focused on hormonal skin and hair conditions.",
                "bio_long": (
                    "Dr. Priya Nair is a Mumbai-based dermatologist specialising in "
                    "hormonally-driven skin and hair disorders — including PCOS-related "
                    "acne, alopecia, and melasma. She completed her MBBS at Grant Medical "
                    "College and her MD in Dermatology at Lokmanya Tilak Municipal Medical College."
                ),
                "photo_url": None,
                "revenue_share_pct": "50.00",
                "credentials": [
                    {"type": CredentialType.MBBS, "institution": "Grant Medical College, Mumbai", "year": 2013},
                    {
                        "type": CredentialType.MD,
                        "institution": "Lokmanya Tilak Municipal Medical College",
                        "year": 2017,
                    },
                ],
            },
        ]

        doctor_orm_by_nmc: dict[str, Doctor] = {}

        for d in doctors_seed:
            # User
            user = await db.scalar(select(User).where(User.phone == d["phone"]))
            if user is None:
                user = User(
                    name=d["name"],
                    role=UserRole.DOCTOR,
                    phone=d["phone"],
                    email=d["email"],
                    password_hash=hash_password("DemoPass123!"),
                    phone_verified=True,
                )
                db.add(user)
                await db.flush()

            # Doctor profile
            doctor = await db.scalar(
                select(Doctor).where(Doctor.nmc_registration_number == d["nmc"])
            )
            if doctor is None:
                doctor = Doctor(
                    user_id=user.id,
                    nmc_registration_number=d["nmc"],
                    nmc_state_council=d["state_council"],
                    verified_at=datetime.now(UTC),
                    specialty=d["specialty"],
                    conditions_treated=d["conditions"],
                    consultation_languages=d["languages"],
                    status=d["status"],
                    bio_short=d["bio_short"],
                    bio_long=d["bio_long"],
                    photo_url=d["photo_url"],
                    revenue_share_pct=d["revenue_share_pct"],
                    onboarding_stage="complete",
                )
                db.add(doctor)
                await db.flush()

                for cred in d["credentials"]:
                    db.add(
                        Credential(
                            doctor_id=doctor.id,
                            credential_type=cred["type"],
                            institution=cred["institution"],
                            year=cred["year"],
                        )
                    )

            doctor_orm_by_nmc[d["nmc"]] = doctor

        # ── Demo coordinator ───────────────────────────────────────────────────

        coord_phone = "+919800000010"
        coord_user = await db.scalar(select(User).where(User.phone == coord_phone))
        if coord_user is None:
            coord_user = User(
                name="Ananya Menon",
                role=UserRole.COORDINATOR,
                phone=coord_phone,
                email="ananya.menon@dev.kyros.local",
                password_hash=hash_password("DemoPass123!"),
                phone_verified=True,
            )
            db.add(coord_user)
            await db.flush()

        coord = await db.scalar(select(Coordinator).where(Coordinator.user_id == coord_user.id))
        if coord is None:
            coord = Coordinator(
                user_id=coord_user.id,
                status=CoordinatorStatus.ACTIVE,
                employee_id="COORD-001",
            )
            db.add(coord)
            await db.flush()

        # ── Demo patients ──────────────────────────────────────────────────────

        patients_seed = [
            {
                "name": "Sunita Reddy",
                "phone": "+919700000001",
                "email": "sunita.reddy@dev.kyros.local",
                "kyros_id": "KYR-2026-00001",
                "conditions": ["thyroid"],
                "allergies": "Penicillin",
                "chronic_conditions": "Hypothyroidism (diagnosed 2021)",
                "current_medications": "Levothyroxine 50mcg once daily",
            },
            {
                "name": "Kavya Krishnamurthy",
                "phone": "+919700000002",
                "email": "kavya.k@dev.kyros.local",
                "kyros_id": "KYR-2026-00002",
                "conditions": ["pcos", "skin_hair"],
                "allergies": None,
                "chronic_conditions": "PCOS (2020), androgenic alopecia",
                "current_medications": "Metformin 500mg twice daily",
            },
            {
                "name": "Rohit Agarwal",
                "phone": "+919700000003",
                "email": "rohit.agarwal@dev.kyros.local",
                "kyros_id": "KYR-2026-00003",
                "conditions": ["weight"],
                "allergies": None,
                "chronic_conditions": "Obesity (BMI 32), pre-diabetes",
                "current_medications": None,
            },
            {
                "name": "Deepa Srinivasan",
                "phone": "+919700000004",
                "email": "deepa.s@dev.kyros.local",
                "kyros_id": "KYR-2026-00004",
                "conditions": ["hormones_trt"],
                "allergies": "Sulfa drugs",
                "chronic_conditions": "Perimenopause",
                "current_medications": None,
            },
            {
                "name": "Vivek Menon",
                "phone": "+919700000005",
                "email": "vivek.menon@dev.kyros.local",
                "kyros_id": "KYR-2026-00005",
                "conditions": ["longevity"],
                "allergies": None,
                "chronic_conditions": None,
                "current_medications": None,
            },
        ]

        assigned_ids: list[str] = []
        for p in patients_seed:
            patient_user = await db.scalar(select(User).where(User.phone == p["phone"]))
            if patient_user is None:
                patient_user = User(
                    name=p["name"],
                    role=UserRole.PATIENT,
                    phone=p["phone"],
                    email=p["email"],
                    password_hash=hash_password("DemoPass123!"),
                    phone_verified=True,
                )
                db.add(patient_user)
                await db.flush()

            patient = await db.scalar(
                select(Patient).where(Patient.user_id == patient_user.id)
            )
            if patient is None:
                # Reserve a patient ID from the sequence
                seq_val = await db.scalar(text("SELECT nextval('kc_patient_id_seq')"))
                kyros_id = p["kyros_id"] if p["kyros_id"] else f"KYR-2026-{seq_val:05d}"
                patient = Patient(
                    user_id=patient_user.id,
                    kyros_patient_id=kyros_id,
                    primary_conditions=p["conditions"],
                    allergies=p["allergies"],
                    chronic_conditions=p["chronic_conditions"],
                    current_medications=p["current_medications"],
                    assigned_coordinator_id=coord.id,
                    intake_complete_at=datetime.now(UTC),
                )
                db.add(patient)
                await db.flush()
            assigned_ids.append(str(patient.id))

        # Keep BOTH sides of the coordinator↔patient link in sync. The
        # coordinator portal scopes every query by Coordinator.assigned_patient_ids,
        # so setting only Patient.assigned_coordinator_id (above) would leave the
        # portal showing no patients and no consultations. Merge idempotently.
        merged = list(coord.assigned_patient_ids or [])
        for pid in assigned_ids:
            if pid not in merged:
                merged.append(pid)
        coord.assigned_patient_ids = merged

        await db.commit()

    print("seed_dev: seeded 3 doctors, 1 coordinator, 5 patients — done.")


if __name__ == "__main__":
    asyncio.run(main())
    sys.exit(0)
