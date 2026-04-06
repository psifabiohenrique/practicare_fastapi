from http import HTTPStatus
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from tests.factories import TreatmentFactory, TreatmentRecordFactory

pytestmark = pytest.mark.asyncio


async def test_get_treatment_record(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    response = client.get(f"/treatment-records/{treatment_record.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert data["uuid"] == str(treatment_record.uuid)
    assert data["treatment_uuid"] == str(treatment.uuid)


async def test_list_treatment_records(session_client, db_session):
    client, user = session_client
    batch_size = 3

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    TreatmentRecordFactory.create_batch(batch_size, treatment=treatment)
    await db_session.commit()

    response = client.get(f"/treatment-records/treatment/{treatment.uuid}")
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    assert len(data) == batch_size


@patch("src.tasks.context_update.generate_context_draft_task.delay")
async def test_create_treatment_record_sequential(
    mock_update_context, session_client, db_session
):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    payload = {
        "treatment_uuid": str(treatment.uuid),
        "date": "2024-01-01",
        "start_time": "10:00:00",
        "end_time": "11:00:00",
        "content": "Record 1",
    }

    # First record
    response = client.post("/treatment-records", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["record_number"] == 1

    # Second record
    payload["content"] = "Record 2"
    response = client.post("/treatment-records", json=payload)
    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["record_number"] == 2  # noqa: PLR2004


async def test_update_treatment_record(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    payload = {"content": "Updated content"}
    response = client.patch(
        f"/treatment-records/{treatment_record.uuid}",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    assert response.json()["content"] == "Updated content"


async def test_get_treatment_record_forbidden(session_client, db_session):
    client, user = session_client

    # Create another user and their treatment
    other_user_uuid = str(uuid4())
    treatment = TreatmentFactory.build(user_uuid=other_user_uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    response = client.get(f"/treatment-records/{treatment_record.uuid}")
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_get_treatment_record_not_found(session_client):
    client, _ = session_client
    random_uuid = str(uuid4())
    response = client.get(f"/treatment-records/{random_uuid}")
    assert response.status_code == HTTPStatus.NOT_FOUND
    assert "detail" in response.json()


async def test_upload_audio_chunked_flow(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # 1. Initialize
    payload = {"session_date": "2024-01-01"}
    response = client.post(
        f"/treatment-records/treatments/{treatment.uuid}/automated-record",
        json=payload,
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    job_uuid = data["job_uuid"]
    assert "record" in data

    # 2. Upload chunks
    for i in range(2):
        chunk_response = client.post(
            f"/treatment-records/automated-record/{job_uuid}/chunk?chunk_index={i}",
            files={"audio_file": ("chunk.webm", b"chunk-data", "audio/webm")},
        )
        assert chunk_response.status_code == HTTPStatus.OK

    # 3. Finalize
    with (
        patch(
            "src.services.automated_record_service.AutomatedRecordService.upload_audio_file"
        ) as mock_upload,
        patch(
            "src.routers.treatment_record_controller.transcribe_audio"
        ) as mock_transcribe,  # noqa: F841
    ):
        mock_upload.return_value = MagicMock(name="test.webm")
        finalize_response = client.post(
            f"/treatment-records/automated-record/{job_uuid}/finalize?total_chunks=2"
        )
        assert finalize_response.status_code == HTTPStatus.OK
        assert finalize_response.json()["status"] == "processing"


async def test_reload_audio_chunked_flow(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    treatment_record = TreatmentRecordFactory.build(
        treatment=treatment, record_number=1
    )
    db_session.add(treatment_record)
    await db_session.commit()
    await db_session.refresh(treatment_record)

    # 1. Initialize Reload
    response = client.post(
        f"/treatment-records/treatments/{treatment_record.uuid}/automated-record-reload"
    )
    assert response.status_code == HTTPStatus.OK
    data = response.json()
    job_uuid = data["job_uuid"]

    # 2. Upload 1 chunk
    chunk_response = client.post(
        f"/treatment-records/automated-record/{job_uuid}/chunk?chunk_index=0",
        files={"audio_file": ("chunk.webm", b"chunk-data", "audio/webm")},
    )
    assert chunk_response.status_code == HTTPStatus.OK

    # 3. Finalize
    with (
        patch(
            "src.services.automated_record_service.AutomatedRecordService.upload_audio_file"
        ) as mock_upload,
        patch(
            "src.routers.treatment_record_controller.transcribe_audio"
        ) as mock_transcribe,  # noqa: F841
    ):
        mock_upload.return_value = MagicMock(name="test.webm")
        finalize_response = client.post(
            f"/treatment-records/automated-record/{job_uuid}/finalize?total_chunks=1"
        )
        assert finalize_response.status_code == HTTPStatus.OK


async def test_upload_audio_chunk_forbidden(session_client, db_session):
    client, user = session_client

    # Create a job belonging to another user
    other_user_uuid = uuid4()
    treatment = TreatmentFactory.build(user_uuid=other_user_uuid)
    db_session.add(treatment)
    await db_session.commit()

    treatment_record = TreatmentRecordFactory.build(treatment=treatment)
    db_session.add(treatment_record)
    await db_session.commit()

    from src.models.automated_record_job import AutomatedRecordJob, JobStatus  # noqa: I001, PLC0415

    job = AutomatedRecordJob(
        user_uuid=other_user_uuid,
        treatment_uuid=treatment.uuid,
        treatment_record_uuid=treatment_record.uuid,
        status=JobStatus.PENDING,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = client.post(
        f"/treatment-records/automated-record/{job.uuid}/chunk?chunk_index=0",
        files={"audio_file": ("chunk.webm", b"data", "audio/webm")},
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_finalize_audio_upload_forbidden(session_client, db_session):
    client, user = session_client

    other_user_uuid = uuid4()
    treatment = TreatmentFactory.build(user_uuid=other_user_uuid)
    db_session.add(treatment)
    await db_session.commit()

    treatment_record = TreatmentRecordFactory.build(treatment=treatment)
    db_session.add(treatment_record)
    await db_session.commit()

    from src.models.automated_record_job import AutomatedRecordJob, JobStatus  # noqa: I001, PLC0415

    job = AutomatedRecordJob(
        user_uuid=other_user_uuid,
        treatment_uuid=treatment.uuid,
        treatment_record_uuid=treatment_record.uuid,
        status=JobStatus.PENDING,
    )
    db_session.add(job)
    await db_session.commit()
    await db_session.refresh(job)

    response = client.post(
        f"/treatment-records/automated-record/{job.uuid}/finalize?total_chunks=1"
    )
    assert response.status_code == HTTPStatus.FORBIDDEN


async def test_finalize_audio_upload_missing_chunks_error(
    session_client, db_session
):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # Initialize
    payload = {"session_date": "2024-01-01"}
    resp = client.post(
        f"/treatment-records/treatments/{treatment.uuid}/automated-record",
        json=payload,
    )
    job_uuid = resp.json()["job_uuid"]

    # Finalize with 2 chunks but uploaded 0
    response = client.post(
        f"/treatment-records/automated-record/{job_uuid}/finalize?total_chunks=2"
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert "Missing chunks" in response.json()["detail"]


async def test_finalize_audio_upload_generic_error(session_client, db_session):
    client, user = session_client

    treatment = TreatmentFactory.build(user=user, user_uuid=user.uuid)
    db_session.add(treatment)
    await db_session.commit()
    await db_session.refresh(treatment)

    # 1. Initialize
    payload = {"session_date": "2024-01-01"}
    response = client.post(
        f"/treatment-records/treatments/{treatment.uuid}/automated-record",
        json=payload,
    )
    job_uuid = response.json()["job_uuid"]

    # 2. Upload 1 chunk
    client.post(
        f"/treatment-records/automated-record/{job_uuid}/chunk?chunk_index=0",
        files={"audio_file": ("chunk.webm", b"chunk-data", "audio/webm")},
    )

    # 3. Finalize with error
    with patch(
        "src.services.automated_record_service.AutomatedRecordService.finalize_chunked_upload",
        side_effect=Exception("Generic error"),
    ):
        finalize_response = client.post(
            f"/treatment-records/automated-record/{job_uuid}/finalize?total_chunks=1"
        )
        assert (
            finalize_response.status_code
            == HTTPStatus.INTERNAL_SERVER_ERROR
        )
        assert "Erro ao processar áudio" in finalize_response.json()["detail"]
