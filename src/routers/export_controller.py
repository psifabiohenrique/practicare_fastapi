import logging
from datetime import datetime

from fastapi import APIRouter
from fastapi.responses import StreamingResponse

from src.routers.deps import CurrentUser, SessionDB
from src.services.export_service import ExportService

router = APIRouter(
    prefix="/export",
    tags=["Export"],
)
logger = logging.getLogger(__name__)


@router.get("/backup")
async def download_backup(
    db: SessionDB,
    current_user: CurrentUser,
):
    logger.info(
        "Iniciando download de backup para usuário %s", current_user.uuid
    )

    zip_buffer = await ExportService.generate_user_backup(
        db, current_user.uuid
    )

    date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    filename = f"backup_prontuarios_{date_str}.zip"

    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
