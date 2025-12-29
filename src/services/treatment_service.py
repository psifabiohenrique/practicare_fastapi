from sqlalchemy.orm import Session

from models import Treatment
from schemas import TreatmentCreate, TreatmentUpdate


class TreatmentService:
    @staticmethod
    def get_treatment(db: Session, treatment_id: int) -> Treatment | None:
        return db.query(Treatment).filter(Treatment.id == treatment_id).first()

    @staticmethod
    def get_treatments(
        db: Session, skip: int = 0, limit: int = 100
    ) -> list[Treatment]:
        return db.query(Treatment).offset(skip).limit(limit).all()

    @staticmethod
    def create_treatment(
        db: Session, treatment_in: TreatmentCreate
    ) -> Treatment:
        db_treatment = TreatmentService._create_treatment_model(treatment_in)
        db.add(db_treatment)
        db.commit()
        db.refresh(db_treatment)
        return db_treatment

    @staticmethod
    def _create_treatment_model(treatment_in: TreatmentCreate) -> Treatment:
        return Treatment(**treatment_in.model_dump())

    @staticmethod
    def update_treatment(
        db: Session, db_treatment: Treatment, treatment_in: TreatmentUpdate
    ) -> Treatment:
        TreatmentService._apply_update(db_treatment, treatment_in)
        db.add(db_treatment)
        db.commit()
        db.refresh(db_treatment)
        return db_treatment

    @staticmethod
    def _apply_update(
        db_treatment: Treatment, treatment_in: TreatmentUpdate
    ) -> None:
        update_data = treatment_in.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(db_treatment, field, value)

    @staticmethod
    def delete_treatment(db: Session, treatment_id: int) -> Treatment | None:
        db_treatment = (
            db.query(Treatment).filter(Treatment.id == treatment_id).first()
        )
        if db_treatment:
            db.delete(db_treatment)
            db.commit()
        return db_treatment
