"""Create or update a staff account (super admin, coordinator, or doctor).

Staff accounts are never created through public signup — this script is the
only bootstrap path. Run it inside the backend container so it reaches the
compose-network Postgres, e.g. on the EC2 over SSM:

    sudo docker run --rm -it --network kyros_default \
        --env-file /etc/kyros/backend.env \
        <ECR_REGISTRY>/kyros-backend:<tag> \
        python scripts/create_staff_user.py \
            --role super_admin --name "Asha Rao" \
            --email asha@kyrosclinic.com --phone +919876543210

The password is prompted interactively (never a CLI argument — it must not
land in shell history). For non-interactive use set KYROS_STAFF_PASSWORD.

Roles:
    super_admin  → logs in at /admin/login
    coordinator  → logs in at /coord/login (Coordinator profile row created)
    doctor       → logs in via the doctor portal (/v1/auth/login).
                   Requires --nmc. Created with status 'applied' unless
                   --activate is passed; verify/activate via /admin/doctors.

Idempotent by phone number: re-running with the same phone and role updates
name/email/password. A role mismatch on an existing phone aborts — this
script never changes an existing account's role.
"""

from __future__ import annotations

import argparse
import asyncio
import getpass
import os
import re
import sys

# Ensure the project root is on sys.path so `import app` works when the script
# is invoked directly via `python scripts/create_staff_user.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

_E164_RE = re.compile(r"^\+[1-9]\d{6,14}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_MIN_PASSWORD_LENGTH = 12

_LOGIN_HINT = {
    "super_admin": "Log in at https://api.kyrosclinic.com/admin/login",
    "coordinator": "Log in at https://api.kyrosclinic.com/coord/login",
    "doctor": "Log in at https://doctor.kyrosclinic.com",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--role", required=True, choices=["super_admin", "coordinator", "doctor"]
    )
    parser.add_argument("--name", required=True)
    parser.add_argument("--email", required=True)
    parser.add_argument("--phone", required=True, help="E.164, e.g. +919876543210")
    # Coordinator
    parser.add_argument("--employee-id", default=None, help="coordinator only")
    # Doctor
    parser.add_argument("--nmc", default=None, help="doctor only: NMC registration number")
    parser.add_argument("--state-council", default=None, help="doctor only")
    parser.add_argument(
        "--specialty", default="", help="doctor only: comma-separated, e.g. endocrinologist"
    )
    parser.add_argument(
        "--languages", default="en", help="doctor only: comma-separated, default en"
    )
    parser.add_argument(
        "--activate",
        action="store_true",
        help="doctor only: mark verified+active immediately instead of 'applied'",
    )
    return parser.parse_args()


def _read_password() -> str:
    env_password = os.environ.get("KYROS_STAFF_PASSWORD")
    if env_password:
        password = env_password
    else:
        password = getpass.getpass("Password for the new account: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            sys.exit("ERROR: passwords do not match.")
    if len(password) < _MIN_PASSWORD_LENGTH:
        sys.exit(f"ERROR: password must be at least {_MIN_PASSWORD_LENGTH} characters.")
    return password


def _validate(args: argparse.Namespace) -> None:
    if not _E164_RE.match(args.phone):
        sys.exit("ERROR: --phone must be E.164, e.g. +919876543210")
    if not _EMAIL_RE.match(args.email):
        sys.exit("ERROR: --email does not look like a valid address")
    if args.role == "doctor" and not args.nmc:
        sys.exit("ERROR: --nmc is required for --role doctor")


async def _run(args: argparse.Namespace, password: str) -> None:
    from datetime import UTC, datetime

    from sqlalchemy import select

    from app.core.audit import AuditContext, write_audit
    from app.core.security import hash_password
    from app.db.enums import ActorRole, CoordinatorStatus, DoctorStatus, UserRole
    from app.db.session import AsyncSessionLocal
    from app.models.admin import Coordinator
    from app.models.doctor import Doctor
    from app.models.identity import User

    role = UserRole(args.role)

    async with AsyncSessionLocal() as db:
        user = await db.scalar(select(User).where(User.phone == args.phone))

        if user is not None and user.role != role:
            sys.exit(
                f"ERROR: {args.phone} already belongs to a user with role "
                f"'{user.role.value}'. This script never changes an existing "
                f"account's role — use a different phone number."
            )

        created = user is None
        if created:
            user = User(
                name=args.name,
                role=role,
                phone=args.phone,
                email=args.email,
                password_hash=hash_password(password),
                phone_verified=True,  # staff skip the patient OTP flow
            )
            db.add(user)
            await db.flush()
        else:
            user.name = args.name
            user.email = args.email
            user.password_hash = hash_password(password)
            user.phone_verified = True
            await db.flush()

        profile_note = ""
        if role == UserRole.COORDINATOR:
            coordinator = await db.scalar(
                select(Coordinator).where(Coordinator.user_id == user.id)
            )
            if coordinator is None:
                db.add(
                    Coordinator(
                        user_id=user.id,
                        status=CoordinatorStatus.ACTIVE,
                        employee_id=args.employee_id or f"COORD-{args.phone[-4:]}",
                    )
                )
                await db.flush()
                profile_note = "Coordinator profile created."
            else:
                profile_note = "Coordinator profile already exists."

        elif role == UserRole.DOCTOR:
            doctor = await db.scalar(select(Doctor).where(Doctor.user_id == user.id))
            if doctor is None:
                doctor = Doctor(
                    user_id=user.id,
                    nmc_registration_number=args.nmc,
                    nmc_state_council=args.state_council,
                    specialty=[s.strip() for s in args.specialty.split(",") if s.strip()],
                    consultation_languages=[
                        lang.strip() for lang in args.languages.split(",") if lang.strip()
                    ],
                    status=DoctorStatus.ACTIVE if args.activate else DoctorStatus.APPLIED,
                    verified_at=datetime.now(UTC) if args.activate else None,
                )
                db.add(doctor)
                await db.flush()
                profile_note = (
                    "Doctor profile created "
                    + ("(active)." if args.activate else
                       "(status 'applied' — verify and activate via /admin/doctors).")
                )
            else:
                profile_note = "Doctor profile already exists (status unchanged)."

        await write_audit(
            db,
            AuditContext(
                actor_user_id=None,
                actor_role=ActorRole.SYSTEM,
                ip_address="127.0.0.1",  # CLI run; audit ip column is INET
                user_agent="scripts/create_staff_user.py",
                request_id="",
            ),
            action="staff_user_created" if created else "staff_user_updated",
            resource_type="user",
            resource_id=user.id,
            allowed=True,
            log_metadata={"role": role.value},
        )

        await db.commit()

        verb = "Created" if created else "Updated"
        print(f"{verb} {role.value} account for {args.name} ({args.phone}).")
        if profile_note:
            print(profile_note)
        print(_LOGIN_HINT[args.role])


def main() -> None:
    args = _parse_args()
    _validate(args)
    password = _read_password()
    asyncio.run(_run(args, password))


if __name__ == "__main__":
    main()


