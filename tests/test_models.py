from http import HTTPStatus

from models import Patient, Treatment, User
from tests.factories import PatientFactory, TreatmentFactory, UserFactory


def test_create_user(db_session):
    user = UserFactory()

    assert user.id is not None
    assert user.uuid is not None
    assert user.name is not None
    assert user.email is not None
    assert user.hashed_password is not None

    # Verify persistence
    db_user = db_session.query(User).filter(User.id == user.id).first()
    assert db_user.email == user.email


def test_create_patient(db_session):
    patient = PatientFactory()
    assert patient.id is not None
    assert patient.uuid is not None
    assert patient.first_name is not None

    db_patient = (
        db_session.query(Patient).filter(Patient.id == patient.id).first()
    )
    assert db_patient.uuid == patient.uuid
    assert db_patient.gender == patient.gender


def test_create_treatment(db_session):
    treatment = TreatmentFactory()
    assert treatment.id is not None
    assert treatment.user_uuid is not None
    assert treatment.patient_uuid is not None

    db_treatment = (
        db_session
        .query(Treatment)
        .filter(Treatment.id == treatment.id)
        .first()
    )
    assert db_treatment.user_uuid == treatment.user_uuid
    assert db_treatment.patient_uuid == treatment.patient_uuid

    # Test relationships
    assert treatment.user is not None
    assert treatment.patient is not None
    assert treatment in treatment.user.treatments
    assert treatment in treatment.patient.treatments


def test_root_endpoint(client):
    response = client.get("/")
    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"Hello": "World"}
