import pytest

from src.core.exceptions import ValidationError
from src.models import Gender, Patient
from src.schemas.patient_schema import PatientCreate, PatientUpdate
from src.services.patient_service import PatientService


class TestCreatePatientModel:
    def test_creates_patient_with_title_case_names(self):
        schema = PatientCreate(
            first_name="  john  ",
            last_name="  doe  ",
        )
        patient = PatientService._create_patient_model(schema)
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"

    def test_creates_patient_with_valid_phone(self):
        schema = PatientCreate(
            first_name="John",
            last_name="Doe",
            phone="11999999999",
        )
        patient = PatientService._create_patient_model(schema)
        assert patient.phone == "+5511999999999"

    def test_creates_patient_with_invalid_phone_raises(self):
        schema = PatientCreate(
            first_name="John",
            last_name="Doe",
            phone="123",
        )
        with pytest.raises(ValidationError):
            PatientService._create_patient_model(schema)

    def test_creates_patient_with_none_phone(self):
        schema = PatientCreate(
            first_name="John",
            last_name="Doe",
            phone=None,
        )
        patient = PatientService._create_patient_model(schema)
        assert patient.phone is None

    def test_creates_patient_with_gender(self):
        schema = PatientCreate(
            first_name="Maria",
            last_name="Silva",
            gender=Gender.FEMALE,
        )
        patient = PatientService._create_patient_model(schema)
        assert patient.gender == Gender.FEMALE


class TestApplyUpdate:
    def test_apply_update_basic_fields(self):
        patient = Patient(first_name="John", last_name="Doe")
        update = PatientUpdate(first_name="Jane")
        PatientService._apply_update(patient, update)
        assert patient.first_name == "Jane"
        assert patient.last_name == "Doe"  # Unchanged

    def test_apply_update_phone_normalization(self):
        patient = Patient(first_name="John", last_name="Doe", phone=None)
        update = PatientUpdate(phone="11999999999")
        PatientService._apply_update(patient, update)
        assert patient.phone == "+5511999999999"

    def test_apply_update_invalid_phone_raises(self):
        patient = Patient(first_name="John", last_name="Doe")
        update = PatientUpdate(phone="123")
        with pytest.raises(ValidationError):
            PatientService._apply_update(patient, update)

    def test_apply_update_empty_does_nothing(self):
        patient = Patient(first_name="John", last_name="Doe")
        update = PatientUpdate()
        PatientService._apply_update(patient, update)
        assert patient.first_name == "John"
        assert patient.last_name == "Doe"
