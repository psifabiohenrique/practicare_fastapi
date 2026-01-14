import asyncio
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent / "src"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from sqlalchemy import func, select

from database import SessionLocal
from models import Treatment, TreatmentRecord, TreatmentReport, User


async def verify_data():
    async with SessionLocal() as session:
        # Get fixed user
        result = await session.execute(
            select(User).where(User.email == "dev@practicare.com")
        )
        user = result.scalar_one_or_none()

        if not user:
            print("User not found!")
            return

        print(f"User: {user.name} ({user.email}), UUID: {user.uuid}")

        # Count treatments
        t_count = await session.execute(
            select(func.count(Treatment.id)).where(
                Treatment.user_uuid == user.uuid
            )
        )
        t_total = t_count.scalar()
        print(f"Treatments: {t_total}")

        # Count patients (unique patients with treatments for this user)
        p_count = await session.execute(
            select(func.count(func.distinct(Treatment.patient_uuid))).where(
                Treatment.user_uuid == user.uuid
            )
        )
        p_total = p_count.scalar()
        print(f"Patients: {p_total}")

        # Count records
        r_count = await session.execute(
            select(func.count(TreatmentRecord.id))
            .join(Treatment)
            .where(Treatment.user_uuid == user.uuid)
        )
        r_total = r_count.scalar()
        print(f"Records: {r_total}")

        # Count reports
        rep_count = await session.execute(
            select(func.count(TreatmentReport.id))
            .join(Treatment)
            .where(Treatment.user_uuid == user.uuid)
        )
        rep_total = rep_count.scalar()
        print(f"Reports: {rep_total}")


if __name__ == "__main__":
    asyncio.run(verify_data())
