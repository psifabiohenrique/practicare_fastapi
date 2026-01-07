from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from models import User
from routers.deps import get_current_user
from schemas.treatment_record_schema import (
    TreatmentRecordRead,
)
from services.treatment_record_service import TreatmentRecordService

router = APIRouter(prefix="/treatment-records", tags=["Treatment records"])

SessionDB = Annotated[AsyncSession, Depends(get_db)]
CurrentUser = Annotated[User, Depends(get_current_user)]


@router.get("/{treatment_record_uuid}", response_model=TreatmentRecordRead)
async def get_treatment_record(
    treatment_record_uuid: str,
    db: SessionDB,
    current_user: CurrentUser,
) -> any:
    print("Treatment record uuid:", treatment_record_uuid)
    result = await TreatmentRecordService.get_treatment_record(
        db, treatment_record_uuid
    )
    print("Treatment record:", result)

    if not result:
        raise HTTPException(
            status_code=404, detail="Treatment record not found"
        )
    if result.treatment.user_uuid != current_user.uuid:
        raise HTTPException(status_code=403, detail="Access denied")
    return result
