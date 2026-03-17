from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest

from src.core.exceptions import ValidationError
from src.models import Patient
from src.schemas import PatientCreate, PatientUpdate
from src.services.patient_service import PatientService


@pytest.fixture
def mock_db():
    db = AsyncMock()
    db.add = MagicMock()
    return db


@pytest.fixture
def mock_patient():
    patient = MagicMock(spec=Patient)
    patient.uuid = uuid4()
    patient.first_name = "John"
    patient.last_name = "Doe"
    patient.phone = "+5511999999999"
    return patient


class TestPatientServiceCRUD:
    @pytest.mark.asyncio
    async def test_get_patient_success(self, mock_db, mock_patient):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_patient
        mock_db.execute.return_value = result_mock

        patient = await PatientService.get_patient(mock_db, mock_patient.uuid)

        assert patient == mock_patient

    @pytest.mark.asyncio
    async def test_get_patient_not_found(self, mock_db):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = result_mock

        patient = await PatientService.get_patient(mock_db, uuid4())

        assert patient is None

    @pytest.mark.asyncio
    async def test_get_patients(self, mock_db, mock_patient):
        result_mock = MagicMock()
        result_mock.scalars.return_value.all.return_value = [mock_patient]
        mock_db.execute.return_value = result_mock

        patients = await PatientService.get_patients(mock_db)

        assert patients == [mock_patient]

    @pytest.mark.asyncio
    async def test_create_patient_normalization(self, mock_db):
        # Using title case and normalization
        patient_in = PatientCreate(
            first_name=" john ",
            last_name=" doe ",
            phone="11999999999",  # BR region default
        )

        patient = await PatientService.create_patient(mock_db, patient_in)

        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
        # +5511999999999 is the normalized E164 for BR
        assert patient.phone == "+5511999999999"
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_patient_invalid_phone(self, mock_db):
        patient_in = PatientCreate(
            first_name="John",
            last_name="Doe",
            phone="invalid-phone",
        )

        with pytest.raises(
            ValidationError, match="Could not parse phone number"
        ):
            await PatientService.create_patient(mock_db, patient_in)

    @pytest.mark.asyncio
    async def test_update_patient_normalization(self, mock_db, mock_patient):
        patient_in = PatientUpdate(phone="11988888888", first_name="Updated")

        updated_patient = await PatientService.update_patient(
            mock_db, mock_patient, patient_in
        )

        # 11988888888 is 11 digits. E164 should be +5511988888888.
        assert updated_patient.phone == "+5511988888888"
        assert updated_patient.first_name == "Updated"
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_update_patient_invalid_phone(self, mock_db, mock_patient):
        patient_in = PatientUpdate(phone="invalid")

        with pytest.raises(
            ValidationError, match="Could not parse phone number"
        ):
            await PatientService.update_patient(
                mock_db, mock_patient, patient_in
            )

    @pytest.mark.asyncio
    async def test_delete_patient(self, mock_db, mock_patient):
        result_mock = MagicMock()
        result_mock.scalars.return_value.first.return_value = mock_patient
        mock_db.execute.return_value = result_mock

        await PatientService.delete_patient(mock_db, mock_patient.uuid)

        mock_db.delete.assert_called_once_with(mock_patient)
        mock_db.commit.assert_called_once()
