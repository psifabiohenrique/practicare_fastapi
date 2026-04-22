import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from src.core.exceptions import ForbiddenError, NotFoundError
from src.schemas.treatment_context_schema import (
    TreatmentContextApplyDraft,
    TreatmentContextUpdate,
)
from src.services.treatment_context_service import TreatmentContextService
from src.ai.ai_result import AIResult

class TestTreatmentContextService:
    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_get_or_create_context_exists(
        self, mock_get_treatment, mock_db, mock_context, mock_treatment
    ):
        # Mock DB select for existing context
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = mock_context
        mock_db.execute.return_value = res_mock

        context = await TreatmentContextService.get_or_create_context(
            mock_db, mock_treatment.uuid, uuid4()
        )

        assert context == mock_context
        mock_get_treatment.assert_called_once()
        mock_db.add.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_get_or_create_context_creates(
        self, mock_get_treatment, mock_db, mock_treatment
    ):
        # Mock DB select for non-existing context
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = res_mock

        context = await TreatmentContextService.get_or_create_context(
            mock_db, mock_treatment.uuid, uuid4()
        )

        assert str(context.treatment_uuid) == str(mock_treatment.uuid)
        mock_db.add.assert_called_once()
        mock_db.commit.assert_called_once()
        mock_db.refresh.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    async def test_get_context_with_pending_draft(
        self, mock_get_or_create, mock_db, mock_context, mock_draft
    ):
        mock_get_or_create.return_value = mock_context
        
        # Mock DB select for draft
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = mock_draft
        mock_db.execute.return_value = res_mock

        ctx, draft = await TreatmentContextService.get_context_with_pending_draft(
            mock_db, mock_context.treatment_uuid, uuid4()
        )

        assert ctx == mock_context
        assert draft == mock_draft

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    async def test_update_context(
        self, mock_get_or_create, mock_db, mock_context
    ):
        mock_get_or_create.return_value = mock_context
        schema = TreatmentContextUpdate(life_dynamics=["New Life Dynamics"])

        updated = await TreatmentContextService.update_context(
            mock_db, mock_context.treatment_uuid, uuid4(), schema
        )

        assert updated.life_dynamics == ["New Life Dynamics"]
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_create_draft(self, mock_db):
        ctx_uuid = uuid4()
        record_uuid = uuid4()
        draft_data = {"life_dynamics": "New suggested dynamics", "ignored_field": "foo"}

        draft = await TreatmentContextService.create_draft(
            mock_db, ctx_uuid, record_uuid, draft_data
        )

        assert str(draft.treatment_context_uuid) == str(ctx_uuid)
        assert str(draft.treatment_record_uuid) == str(record_uuid)
        assert draft.life_dynamics == "New suggested dynamics"
        mock_db.add.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    async def test_schedule_context_generation_success(self, mock_get_or_create, mock_db, mock_context):
        mock_get_or_create.return_value = mock_context
        mock_context.is_update_scheduled = False
        
        with patch("src.tasks.context_generation.generate_context_from_history_task.delay") as mock_delay:
            await TreatmentContextService.schedule_context_generation(mock_db, uuid4(), uuid4(), "notes", True)
            assert mock_context.is_update_scheduled is True
            mock_delay.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_apply_draft_success(
        self, mock_get_treatment, mock_db, mock_draft, mock_context
    ):
        res_draft = MagicMock()
        res_draft.scalars.return_value.first.return_value = mock_draft
        res_context = MagicMock()
        res_context.scalars.return_value.first.return_value = mock_context
        mock_db.execute.side_effect = [res_draft, res_context, res_context]

        final_data = TreatmentContextApplyDraft(life_dynamics=["Finalized dynamics"])
        result = await TreatmentContextService.apply_draft(
            mock_db, mock_draft.uuid, uuid4(), final_data
        )

        assert result.life_dynamics == ["Finalized dynamics"]
        assert mock_draft.is_applied is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_apply_draft_already_applied(self, mock_get_treatment, mock_db, mock_draft, mock_context):
        mock_draft.is_applied = True
        res_draft = MagicMock()
        res_draft.scalars.return_value.first.return_value = mock_draft
        res_context = MagicMock()
        res_context.scalars.return_value.first.return_value = mock_context
        mock_db.execute.side_effect = [res_draft, res_context]

        with pytest.raises(ForbiddenError, match="This draft has already been applied"):
            await TreatmentContextService.apply_draft(
                mock_db, mock_draft.uuid, uuid4(), TreatmentContextApplyDraft()
            )

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_reject_draft_success(
        self, mock_get_treatment, mock_db, mock_draft, mock_context
    ):
        res_draft = MagicMock()
        res_draft.scalars.return_value.first.return_value = mock_draft
        res_context = MagicMock()
        res_context.scalars.return_value.first.return_value = mock_context
        mock_db.execute.side_effect = [res_draft, res_context]

        await TreatmentContextService.reject_draft(
            mock_db, mock_draft.uuid, uuid4()
        )

        assert mock_draft.is_applied is True
        mock_db.commit.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_draft_with_auth_not_found(self, mock_db):
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = res_mock
        
        with pytest.raises(NotFoundError, match="Treatment context draft not found"):
            await TreatmentContextService._get_draft_with_auth(mock_db, uuid4(), uuid4())

    @pytest.mark.asyncio
    async def test_get_draft_with_auth_context_not_found(self, mock_db, mock_draft):
        res_draft = MagicMock()
        res_draft.scalars.return_value.first.return_value = mock_draft
        res_none = MagicMock()
        res_none.scalars.return_value.first.return_value = None
        mock_db.execute.side_effect = [res_draft, res_none]
        
        with pytest.raises(NotFoundError, match="Treatment context not found"):
            await TreatmentContextService._get_draft_with_auth(mock_db, mock_draft.uuid, uuid4())

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentService.get_treatment_by_uuid")
    async def test_reject_draft_already_processed(self, mock_get_treatment, mock_db, mock_draft, mock_context):
        mock_draft.is_applied = True
        res_draft = MagicMock()
        res_draft.scalars.return_value.first.return_value = mock_draft
        res_context = MagicMock()
        res_context.scalars.return_value.first.return_value = mock_context
        mock_db.execute.side_effect = [res_draft, res_context]
        
        with pytest.raises(ForbiddenError, match="This draft has already been processed"):
            await TreatmentContextService.reject_draft(mock_db, mock_draft.uuid, uuid4())

    @pytest.mark.asyncio
    async def test_merge_pending_draft_into(self, mock_db, mock_context, mock_draft):
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = mock_draft
        mock_db.execute.return_value = res_mock
        
        mock_draft.life_dynamics = {"add": ["Old"], "remove": []}
        mock_draft.clinical_history = None
        mock_draft.psychological_patterns = {"add": ["Same"], "remove": ["Old"]}
        mock_draft.therapeutic_goals = None
        mock_draft.medication_notes = None
        
        new_data = {
            "life_dynamics": {"add": ["New"], "remove": []},
            "clinical_history": {"add": ["History"], "remove": []},
            "psychological_patterns": {"add": ["Same"], "remove": ["Old"]},
            "therapeutic_goals": {"add": ["Goals"], "remove": []}
        }
        
        merged = await TreatmentContextService._merge_pending_draft_into(mock_db, mock_context, new_data)
        
        assert merged["life_dynamics"] == {"add": ["Old", "New"], "remove": []}
        assert merged["clinical_history"] == {"add": ["History"], "remove": []}
        assert merged["psychological_patterns"] == {"add": ["Same"], "remove": ["Old"]}
        assert merged["therapeutic_goals"] == {"add": ["Goals"], "remove": []}
        assert mock_draft.is_applied is True

    @pytest.mark.asyncio
    async def test_merge_pending_draft_into_no_changes(self, mock_db, mock_context, mock_draft):
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = mock_draft
        mock_db.execute.return_value = res_mock
        
        # Draft has empty dicts, new_data has empty dicts to reach line 60
        # instead of the early return for None
        empty_diff = {"add": [], "remove": []}
        mock_draft.life_dynamics = empty_diff
        mock_draft.clinical_history = empty_diff
        mock_draft.psychological_patterns = empty_diff
        mock_draft.therapeutic_goals = empty_diff
        mock_draft.medication_notes = empty_diff
        
        new_data = {
            "life_dynamics": empty_diff,
            "clinical_history": empty_diff
        }
        merged = await TreatmentContextService._merge_pending_draft_into(mock_db, mock_context, new_data)
        
        # All fields should be None because _merge_diffs returned None for all at line 60
        assert all(v is None for v in merged.values())

    @pytest.mark.asyncio
    async def test_merge_pending_draft_into_old_only(self, mock_db, mock_context, mock_draft):
        res_mock = MagicMock()
        res_mock.scalars.return_value.first.return_value = mock_draft
        mock_db.execute.return_value = res_mock
        
        mock_draft.life_dynamics = {"add": ["Old"], "remove": []}
        mock_draft.clinical_history = None
        mock_draft.psychological_patterns = None
        mock_draft.therapeutic_goals = None
        mock_draft.medication_notes = None
        
        new_data = {}
        merged = await TreatmentContextService._merge_pending_draft_into(mock_db, mock_context, new_data)
        assert merged["life_dynamics"] == {"add": ["Old"], "remove": []}

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    async def test_schedule_context_generation_already_scheduled(self, mock_get_or_create, mock_db, mock_context):
        mock_context.is_update_scheduled = True
        mock_get_or_create.return_value = mock_context
        
        with pytest.raises(ForbiddenError, match="An update is already scheduled"):
            await TreatmentContextService.schedule_context_generation(mock_db, uuid4(), uuid4(), None, False)

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    @patch("src.services.treatment_context_service.PatientWithTreatmentService.get_patient_with_treatment_uuid")
    async def test_generate_context_from_history_no_material(self, mock_get_patient, mock_get_or_create, mock_db, mock_context, mock_patient):
        mock_get_or_create.return_value = mock_context
        mock_get_patient.return_value = mock_patient
        res_records = MagicMock()
        res_records.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = res_records
        
        await TreatmentContextService.generate_context_from_history(mock_db, mock_context.treatment_uuid, uuid4(), None, True)
        assert mock_context.is_update_scheduled is False

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    @patch("src.services.treatment_context_service.PatientWithTreatmentService.get_patient_with_treatment_uuid")
    @patch("src.services.treatment_context_service.UsageStatisticService.create_statistic")
    async def test_generate_context_from_history_no_records(
        self, mock_create_stat, mock_get_patient, mock_get_or_create, mock_db, mock_context, mock_patient
    ):
        mock_get_or_create.return_value = mock_context
        mock_get_patient.return_value = mock_patient
        res_pending = MagicMock()
        res_pending.scalars.return_value.all.return_value = []
        res_latest = MagicMock()
        res_latest.scalars.return_value.first.return_value = None
        mock_db.execute.side_effect = [res_pending, res_latest]

        with patch("src.ai.chains.context_generation.ContextGenerationChain.generate") as mock_gen:
            mock_gen.return_value = MagicMock(input_tokens=100, output_tokens=200, content={"clinical_history": "Direct update"})
            await TreatmentContextService.generate_context_from_history(mock_db, mock_context.treatment_uuid, uuid4(), "Notes", False)
            assert mock_context.clinical_history == "Direct update"

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.ContextUpdateChain")
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    @patch("src.services.treatment_context_service.TreatmentRecordService.get_treatment_record")
    @patch("src.services.treatment_context_service.PatientWithTreatmentService.get_patient_with_treatment_uuid")
    @patch("src.services.treatment_context_service.UsageStatisticService.create_statistic")
    @patch("src.services.treatment_context_service.TreatmentContextService.create_draft")
    async def test_generate_context_draft(
        self, mock_create_draft, mock_create_stat, mock_get_patient, mock_get_record, mock_get_or_create_ctx, mock_chain_class, mock_db, mock_context, mock_record, mock_patient
    ):
        mock_get_or_create_ctx.return_value = mock_context
        mock_get_record.return_value = mock_record
        mock_get_patient.return_value = mock_patient
        mock_chain = mock_chain_class.return_value
        mock_chain.generate = AsyncMock(return_value=MagicMock(input_tokens=10, output_tokens=20, content={"life_dynamics": "AI suggestion"}))
        res_pending = MagicMock()
        res_pending.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = res_pending

        await TreatmentContextService.generate_context_draft(mock_db, mock_context.treatment_uuid, mock_record.uuid, uuid4())
        mock_chain.generate.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.ContextUpdateChain")
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    @patch("src.services.treatment_context_service.TreatmentRecordService.get_treatment_record")
    @patch("src.services.treatment_context_service.PatientWithTreatmentService.get_patient_with_treatment_uuid")
    @patch("src.services.treatment_context_service.UsageStatisticService.create_statistic")
    @patch("src.services.treatment_context_service.TreatmentContextService.create_draft")
    async def test_generate_context_draft_non_dict(
        self, mock_create_draft, mock_create_stat, mock_get_patient, mock_get_record, mock_get_or_create_ctx, mock_chain_class, mock_db, mock_context, mock_record, mock_patient
    ):
        mock_get_or_create_ctx.return_value = mock_context
        mock_get_record.return_value = mock_record
        mock_get_patient.return_value = mock_patient
        mock_chain = mock_chain_class.return_value
        # AI returns a string instead of a dict
        mock_chain.generate = AsyncMock(return_value=MagicMock(input_tokens=10, output_tokens=20, content="Invalid content"))
        res_pending = MagicMock()
        res_pending.scalars.return_value.first.return_value = None
        mock_db.execute.return_value = res_pending

        await TreatmentContextService.generate_context_draft(mock_db, mock_context.treatment_uuid, mock_record.uuid, uuid4())
        mock_create_draft.assert_called_with(db=mock_db, treatment_context_uuid=mock_context.uuid, treatment_record_uuid=mock_record.uuid, draft_data={})

    @pytest.mark.asyncio
    @patch("src.services.treatment_context_service.TreatmentContextService.get_or_create_context")
    @patch("src.services.treatment_context_service.PatientWithTreatmentService.get_patient_with_treatment_uuid")
    @patch("src.services.treatment_context_service.UsageStatisticService.create_statistic")
    async def test_generate_context_from_history_clears_drafts(
        self, mock_create_stat, mock_get_patient, mock_get_or_create, mock_db, mock_context, mock_patient, mock_record
    ):
        mock_get_or_create.return_value = mock_context
        mock_get_patient.return_value = mock_patient
        res_records = MagicMock()
        res_records.scalars.return_value.all.return_value = [mock_record]
        pending_mock = MagicMock()
        pending_mock.is_applied = False
        res_pending = MagicMock()
        res_pending.scalars.return_value.all.return_value = [pending_mock]
        res_latest = MagicMock()
        res_latest.scalars.return_value.first.return_value = mock_record
        mock_db.execute.side_effect = [res_records, res_pending, res_latest]

        with patch("src.ai.chains.context_generation.ContextGenerationChain.generate") as mock_gen:
            mock_gen.return_value = MagicMock(input_tokens=100, output_tokens=200, content="Not a dict")
            with patch("src.services.treatment_context_service.TreatmentContextService.create_draft") as mock_create_draft:
                await TreatmentContextService.generate_context_from_history(mock_db, mock_context.treatment_uuid, uuid4(), "Old notes", True)
                assert pending_mock.is_applied is True
                expected_draft_data = {
                    "life_dynamics": None,
                    "clinical_history": None,
                    "psychological_patterns": None,
                    "therapeutic_goals": None,
                    "medication_notes": None,
                    "techniques": None,
                    "requested_activities": None,
                }
                mock_create_draft.assert_called_with(db=mock_db, treatment_context_uuid=mock_context.uuid, treatment_record_uuid=mock_record.uuid, draft_data=expected_draft_data)
