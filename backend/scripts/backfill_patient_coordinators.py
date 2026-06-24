"""Backfill: assign a care coordinator to every patient that has none.

Patients created before coordinator auto-assignment (see
``app/repositories/patients.ensure_coordinator_assigned``) have
``assigned_coordinator_id=None``. Their consultation requests are therefore
created unassigned and never surface in any coordinator's queue (the coordinator
portal scopes strictly to its ``assigned_patient_ids``). This one-off script
routes each such patient to the least-loaded active coordinator, keeping both
sides in sync: ``kc_patients.assigned_coordinator_id`` and the coordinator's
``assigned_patient_ids`` JSONB list.

It balances the batch incrementally — each assignment increments the chosen
coordinator's running load so patients spread evenly rather than piling onto
whoever started emptiest.

Dry-run by default; pass --apply to commit. Run inside the backend container so
it reaches the compose-network Postgres:

    make shell-backend
    python scripts/backfill_patient_coordinators.py            # preview
    python scripts/backfill_patient_coordinators.py --apply     # commit
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys

# Ensure the project root is on sys.path so `import app` works when the script
# is invoked directly via `python scripts/backfill_patient_coordinators.py`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


async def _run(apply: bool) -> None:
    from sqlalchemy import select

    from app.db.enums import CoordinatorStatus
    from app.db.session import AsyncSessionLocal
    from app.models.admin import Coordinator
    from app.models.clinic import Patient

    async with AsyncSessionLocal() as db:
        coordinators = (
            await db.scalars(
                select(Coordinator).where(
                    Coordinator.status == CoordinatorStatus.ACTIVE,
                    Coordinator.deleted_at.is_(None),
                )
            )
        ).all()
        if not coordinators:
            sys.exit("ERROR: no active coordinators exist — nothing to assign to.")

        unassigned = (
            await db.scalars(
                select(Patient)
                .where(
                    Patient.assigned_coordinator_id.is_(None),
                    Patient.deleted_at.is_(None),
                )
                .order_by(Patient.created_at)
            )
        ).all()

        if not unassigned:
            print("No unassigned patients. Nothing to do.")
            return

        # Running per-coordinator load so the batch spreads evenly.
        load = {c.id: len(c.assigned_patient_ids) for c in coordinators}
        by_id = {c.id: c for c in coordinators}

        mode = "APPLY" if apply else "DRY-RUN"
        print(f"[{mode}] {len(unassigned)} unassigned patient(s), "
              f"{len(coordinators)} active coordinator(s).\n")

        for patient in unassigned:
            target_id = min(load, key=lambda cid: load[cid])
            target = by_id[target_id]
            pid = str(patient.id)
            label = patient.kyros_patient_id or str(patient.id)
            print(f"  {label} -> coordinator {target_id} (current load {load[target_id]})")
            if apply:
                if pid not in target.assigned_patient_ids:
                    target.assigned_patient_ids = [*target.assigned_patient_ids, pid]
                patient.assigned_coordinator_id = target_id
            load[target_id] += 1

        if apply:
            await db.commit()
            print(f"\nApplied: assigned {len(unassigned)} patient(s).")
        else:
            print(f"\nDry-run only: {len(unassigned)} patient(s) would be assigned. "
                  "Re-run with --apply to commit.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--apply",
        action="store_true",
        help="commit the assignments (default: dry-run preview only)",
    )
    args = parser.parse_args()
    asyncio.run(_run(args.apply))


if __name__ == "__main__":
    main()
