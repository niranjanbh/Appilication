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
    super_admin  → logs in at /admin/login (full access)
    admin        → logs in at /admin/login (read-only: can view every page,
                   cannot suspend users, verify/activate doctors, set revenue
                   share, or publish/archive content)
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
    "admin": "Log in at https://api.kyrosclinic.com/admin/login (read-only tier)",
    "coordinator": "Log in at https://api.kyrosclinic.com/coord/login",
    "doctor": "Log in at https://doctor.kyrosclinic.com",
}


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--role",
        required=True,
        choices=["super_admin", "admin", "coordinator", "doctor"],
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
    from app.core.audit import AuditContext

    from app.db.enums import ActorRole, UserRole
    from app.db.session import AsyncSessionLocal
    from app.services.staff_service import StaffServiceError, create_staff_user

    role = UserRole(args.role)
    ctx = AuditContext(
        actor_user_id=None,
        actor_role=ActorRole.SYSTEM,
        ip_address="127.0.0.1",  # CLI run; audit ip column is INET
        user_agent="scripts/create_staff_user.py",
        request_id="",
    )

    async with AsyncSessionLocal() as db:
        try:
            result = await create_staff_user(
                db,
                ctx,
                role=role,
                name=args.name,
                email=args.email,
                phone=args.phone,
                password=password,
                employee_id=args.employee_id,
                nmc=args.nmc,
                state_council=args.state_council,
                specialty=[s.strip() for s in args.specialty.split(",") if s.strip()],
                languages=[
                    lang.strip() for lang in args.languages.split(",") if lang.strip()
                ],
                activate_doctor=args.activate,
            )
        except StaffServiceError as exc:
            sys.exit(f"ERROR: {exc}")

        await db.commit()

        verb = "Created" if result.created else "Updated"
        print(f"{verb} {role.value} account for {args.name} ({args.phone}).")
        if result.profile_note:
            print(result.profile_note)
        print(_LOGIN_HINT[args.role])


def main() -> None:
    args = _parse_args()
    _validate(args)
    password = _read_password()
    asyncio.run(_run(args, password))


if __name__ == "__main__":
    main()
