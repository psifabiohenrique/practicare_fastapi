from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest

from src.core.exceptions import ForbiddenError, NotFoundError
from src.models import (
    Gender,
    Patient,
    Treatment,
    TreatmentStatus,
    Weekdays,
)
from src.services.patient_with_treatment_service import (
    PatientWithTreatmentService,
)


class TestPatientWithTreatmentServiceRetrieval:
    @pytest.mark.asyncio
    async def test_get_patient_with_treatment_uuid_success(
        self, mock_db, mock_patient, mock_treatment
    ):
        mock_treatment.patient_uuid = mock_patient.uuid
        mock_patient.treatments = [mock_treatment]
        user_uuid = mock_treatment.user_uuid

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_patient
        mock_db.execute.return_value = result_mock

        result = (
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                mock_db, mock_treatment.uuid, user_uuid
            )
        )

        assert result == mock_patient

    @pytest.mark.asyncio
    async def test_get_patient_with_treatment_uuid_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(
            NotFoundError, match="Patient or Treatment not found"
        ):
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                mock_db, uuid4(), "some-user"
            )

    @pytest.mark.asyncio
    async def test_get_patient_with_treatment_uuid_forbidden(
        self, mock_db, mock_patient, mock_treatment
    ):
        mock_treatment.patient_uuid = mock_patient.uuid
        mock_patient.treatments = [mock_treatment]
        wrong_user = "wrong-user-uuid"

        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_patient
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await PatientWithTreatmentService.get_patient_with_treatment_uuid(
                mock_db, mock_treatment.uuid, wrong_user
            )

    @pytest.mark.asyncio
    async def test_get_patients_with_user_uuid(self, mock_db, mock_patient):
        result_mock = MagicMock()
        scalars_mock = result_mock.scalars.return_value
        unique_mock = scalars_mock.unique.return_value
        unique_mock.all.return_value = [mock_patient]
        mock_db.execute.return_value = result_mock

        result = await PatientWithTreatmentService.get_patients_with_user_uuid(
            mock_db, "user-123"
        )

        assert result == [mock_patient]

    @pytest.mark.asyncio
    async def test_get_treatment_with_patient_uuid(
        self, mock_db, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        result = (
            await PatientWithTreatmentService.get_treatment_with_patient_uuid(
                mock_db, mock_treatment.patient_uuid
            )
        )

        assert result == mock_treatment

    @pytest.mark.asyncio
    async def test_get_treatment_with_treatment_uuid_success(
        self, mock_db, mock_treatment
    ):
        # Service converts to str in query but we compare as object or str
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock
        result = await PatientWithTreatmentService.get_treatment_with_treatment_uuid(  # noqa: E501
            mock_db,
            mock_treatment.uuid,
            mock_treatment.user_uuid,
        )

        assert result == mock_treatment

    @pytest.mark.asyncio
    async def test_get_treatment_with_treatment_uuid_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        with pytest.raises(NotFoundError, match="Treatment not found"):
            await (
                PatientWithTreatmentService.get_treatment_with_treatment_uuid(
                    mock_db, uuid4(), "user-123"
                )
            )

    @pytest.mark.asyncio
    async def test_get_treatment_with_treatment_uuid_forbidden(
        self, mock_db, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = result_mock

        with pytest.raises(ForbiddenError, match="Access denied"):
            await (
                PatientWithTreatmentService.get_treatment_with_treatment_uuid(
                    mock_db, mock_treatment.uuid, "wrong-user"
                )
            )

    @pytest.mark.asyncio
    async def test_get_treatments_with_user_uuid_filtering(
        self, mock_db, mock_treatment
    ):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_treatment]
        mock_db.execute.return_value = result_mock

        # Test with various filters to trigger different branches
        result = await (
            PatientWithTreatmentService.get_treatments_with_user_uuid(
                mock_db,
                user_uuid=mock_treatment.user_uuid,
                gender=Gender.FEMALE,
                weekday=Weekdays.TUESDAY,
                status=TreatmentStatus.INACTIVE,
                search="John",
                order_by="name",
                order_dir="desc",
            )
        )

        assert result == [mock_treatment]

        # Test birth_date sorting (asc)
        await PatientWithTreatmentService.get_treatments_with_user_uuid(
            mock_db,
            user_uuid=mock_treatment.user_uuid,
            order_by="birth_date",
            order_dir="asc",
        )

        # Test birth_date sorting (desc)
        await PatientWithTreatmentService.get_treatments_with_user_uuid(
            mock_db,
            user_uuid=mock_treatment.user_uuid,
            order_by="birth_date",
            order_dir="desc",
        )

        # Test name sorting (asc) and default status
        await PatientWithTreatmentService.get_treatments_with_user_uuid(
            mock_db,
            user_uuid=mock_treatment.user_uuid,
            order_by="name",
            order_dir="asc",
        )

    @pytest.mark.asyncio
    async def test_get_daily_treatments(self, mock_db, mock_treatment):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_treatment]
        mock_db.execute.return_value = result_mock

        # Explicit weekday
        result = await PatientWithTreatmentService.get_daily_treatments(
            mock_db, mock_treatment.user_uuid, Weekdays.WEDNESDAY
        )
        assert result == [mock_treatment]

        # Default weekday (now)
        result = await PatientWithTreatmentService.get_daily_treatments(
            mock_db, mock_treatment.user_uuid
        )
        assert result == [mock_treatment]


class TestPatientWithTreatmentServiceModification:
    @pytest.mark.asyncio
    @patch("src.services.patient_with_treatment_service.PatientService")
    @patch("src.services.patient_with_treatment_service.TreatmentService")
    async def test_create_patient_with_treatment(
        self,
        MockTreatmentService,
        MockPatientService,
        mock_db,
        mock_patient,
        mock_treatment,
    ):
        schema = MagicMock()
        schema.patient_schema = MagicMock()
        schema.treatment_schema = MagicMock()

        mock_patient.uuid = uuid4()
        MockPatientService._create_patient_model.return_value = mock_patient
        MockTreatmentService._create_treatment_model.return_value = (
            mock_treatment
        )

        (
            patient,
            treatment,
        ) = await PatientWithTreatmentService.create_patient_with_treatment(
            mock_db, schema, "user-uuid"
        )

        assert patient == mock_patient
        assert treatment == mock_treatment
        assert treatment.patient_uuid == mock_patient.uuid
        mock_db.commit.assert_called_once()
        assert mock_db.refresh.call_count == 2

    @pytest.mark.asyncio
    @patch("src.services.patient_with_treatment_service.PatientService")
    @patch("src.services.patient_with_treatment_service.TreatmentService")
    async def test_update_patient_with_treatment_success(
        self,
        MockTreatmentService,
        MockPatientService,
        mock_db,
        mock_patient,
        mock_treatment,
    ):
        # Mock retrieval of treatment
        mock_treatment.patient_uuid = mock_patient.uuid
        res_treatment = MagicMock()
        res_treatment.scalars.return_value.first.return_value = mock_treatment

        # Mock retrieval of patient
        res_patient = MagicMock()
        res_patient.scalars.return_value.first.return_value = mock_patient

        # Mock final scalar_one result
        res_final = MagicMock()
        res_final.scalar_one.return_value = mock_treatment

        mock_db.execute.side_effect = [res_treatment, res_patient, res_final]

        schema = MagicMock()
        schema.patient_schema = MagicMock()
        schema.treatment_schema = MagicMock()

        result = (
            await PatientWithTreatmentService.update_patient_with_treatment(
                mock_db,
                mock_treatment.uuid,
                mock_treatment.user_uuid,
                schema,
            )
        )

        assert result == mock_treatment
        MockPatientService._apply_update.assert_called_once()
        MockTreatmentService._apply_update.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_patient_with_treatment_patient_not_found(
        self, mock_db, mock_treatment
    ):
        # Mock retrieval of treatment (success)
        res_treatment = MagicMock()
        res_treatment.scalars.return_value.first.return_value = mock_treatment

        # Mock retrieval of patient (fails)
        res_patient = MagicMock()
        res_patient.scalars.return_value.first.return_value = None

        mock_db.execute.side_effect = [res_treatment, res_patient]

        schema = MagicMock()

        with pytest.raises(
            NotFoundError, match="Associated patient not found"
        ):
            await PatientWithTreatmentService.update_patient_with_treatment(
                mock_db,
                mock_treatment.uuid,
                mock_treatment.user_uuid,
                schema,
            )

    @pytest.mark.asyncio
    @patch("src.services.patient_with_treatment_service.TreatmentService")
    async def test_change_treatment_status_toggle(
        self, MockTreatmentService, mock_db, mock_treatment
    ):
        # Mock retrieval of treatment
        res_treatment = MagicMock()
        res_treatment.scalars.return_value.first.return_value = mock_treatment
        mock_db.execute.return_value = res_treatment

        # IMPORTANT: Mock update_treatment as ASYNC!
        MockTreatmentService.update_treatment = AsyncMock()

        # Test ACTIVE to INACTIVE
        mock_treatment.status = TreatmentStatus.ACTIVE
        await PatientWithTreatmentService.change_treatment_status(
            mock_db, mock_treatment.uuid, mock_treatment.user_uuid
        )
        args, _ = MockTreatmentService.update_treatment.call_args
        assert args[2].status == TreatmentStatus.INACTIVE

        # Test INACTIVE to ACTIVE
        mock_treatment.status = TreatmentStatus.INACTIVE
        await PatientWithTreatmentService.change_treatment_status(
            mock_db, mock_treatment.uuid, mock_treatment.user_uuid
        )
        args, _ = MockTreatmentService.update_treatment.call_args
        assert args[2].status == TreatmentStatus.ACTIVE
