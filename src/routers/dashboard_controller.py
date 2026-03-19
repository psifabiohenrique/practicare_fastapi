from datetime import date

from fastapi import APIRouter, Query

from src.routers.deps import CurrentUser, SessionDB
from src.schemas.dashboard_schema import DashboardResponse
from src.services.dashboard_service import DashboardService

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/statistics", response_model=DashboardResponse)
async def get_dashboard_statistics(
    db: SessionDB,
    current_user: CurrentUser,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
) -> DashboardResponse:
    return await DashboardService.get_dashboard(
        db=db,
        user_uuid=current_user.uuid,
        start_date=start_date,
        end_date=end_date,
    )
