import asyncio
import random
import sys
from datetime import date, time, timedelta
from pathlib import Path

# Add src to sys.path to allow imports from models, database, etc.
sys.path.append(str(Path(__file__).parent.parent / "src"))

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from faker import Faker
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import SessionLocal
from models import (
    Gender,
    Patient,
    Treatment,
    TreatmentRecord,
    TreatmentReport,
    User,
    Weekdays,
)
from security import get_password_hash

faker = Faker(["pt_BR"])

FIXED_USER_EMAIL = "dev@dev.com"
FIXED_USER_NAME = "Dev User"
FIXED_USER_PASSWORD = "dev"


async def get_or_create_fixed_user(session: AsyncSession) -> str:
    """Gets the fixed dev user or creates it if it doesn't exist.
    Returns the user UUID."""
    result = await session.execute(
        select(User).where(User.email == FIXED_USER_EMAIL)
    )
    user = result.scalar_one_or_none()

    if not user:
        print(f"Creating fixed user: {FIXED_USER_EMAIL}")
        user = User(
            name=FIXED_USER_NAME,
            email=FIXED_USER_EMAIL,
            hashed_password=get_password_hash(FIXED_USER_PASSWORD),
        )
        session.add(user)
        await session.commit()
        # After commit, user is expired. Re-fetch to get UUID or fetch
        #  it before commit.
        # But wait, we can just use the object before commit if we flush.

        # Fresh session for clean fetch
        async with SessionLocal() as new_session:
            result = await new_session.execute(
                select(User.uuid).where(User.email == FIXED_USER_EMAIL)
            )
            user_uuid = result.scalar_one()
    else:
        print(f"Fixed user already exists: {FIXED_USER_EMAIL}")
        user_uuid = user.uuid

    return user_uuid


async def seed_data():  # noqa: PLR0914
    # 1. Get fixed user UUID using a temporary session
    async with SessionLocal() as session:
        user_uuid = await get_or_create_fixed_user(session)

    # 2. Start seeding with a main session
    # We use a new session and avoid keeping objects across commits.
    async with SessionLocal() as session:
        num_patients = random.randint(10, 50)
        print(f"Generating {num_patients} patients...")

        for i in range(num_patients):
            # Create Patient
            gender = random.choice(list(Gender))
            first_name = (
                faker.first_name_female()
                if gender == Gender.FEMALE
                else faker.first_name_male()
            )
            last_name = faker.last_name()

            patient = Patient(
                first_name=first_name,
                last_name=last_name,
                email=faker.email(),
                phone=faker.cellphone_number(),
                birth_date=faker.date_of_birth(minimum_age=18, maximum_age=90),
                gender=gender,
            )
            session.add(patient)
            await session.flush()  # To populate defaults
            patient_uuid = patient.uuid

            # Create 1 Treatment for this patient linked to the fixed user
            weekday = random.choice(list(Weekdays))
            start_hour = random.randint(8, 17)
            start_time = time(start_hour, 0)
            end_time = time(start_hour + 1, 0)

            treatment = Treatment(
                user_uuid=user_uuid,
                patient_uuid=patient_uuid,
                weekday=weekday,
                start_time=start_time,
                end_time=end_time,
            )
            session.add(treatment)
            await session.flush()
            treatment_uuid = treatment.uuid

            # Create random number of TreatmentRecords (5-15)
            num_records = random.randint(5, 15)
            for j in range(num_records):
                record_date = date.today() - timedelta(
                    days=random.randint(1, 365)
                )
                record = TreatmentRecord(
                    treatment_uuid=treatment_uuid,
                    date=record_date,
                    start_time=start_time,
                    end_time=end_time,
                    content=faker.paragraph(nb_sentences=5),
                    record_number=j + 1,
                )
                session.add(record)

            # Create random number of TreatmentReports (2-5)
            num_reports = random.randint(2, 5)
            for k in range(num_reports):
                issue_date = date.today() - timedelta(
                    days=random.randint(0, 30)
                )
                start_period = issue_date - timedelta(days=90)
                end_period = issue_date - timedelta(days=1)

                report = TreatmentReport(
                    treatment_uuid=treatment_uuid,
                    demand_description=faker.paragraph(),
                    procedures=faker.paragraph(),
                    analysis=faker.paragraph(),
                    conclusion=faker.paragraph(),
                    issue_date=issue_date,
                    start_date_period=start_period,
                    end_date_period=end_period,
                )
                session.add(report)

            if (i + 1) % 10 == 0:
                print(f"  Processed {i + 1} patients...")
                await session.commit()
                # Objects are expired here, but we use _uuid variables
                # from local scope!

        await session.commit()
        print("Seeding completed successfully!")


if __name__ == "__main__":
    try:
        asyncio.run(seed_data())
    except Exception as e:
        print(f"Error during seeding: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
