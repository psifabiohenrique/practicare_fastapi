"""Convert treatment context and draft fields from Text to JSON (list format).

Revision ID: c1d2e3f4a5b6
Revises: f71506e547e2
Create Date: 2026-04-13

"""
import json
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c1d2e3f4a5b6"
down_revision: Union[str, None] = "f71506e547e2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTEXT_FIELDS = [
    "life_dynamics",
    "clinical_history",
    "psychological_patterns",
    "therapeutic_goals",
    "medication_notes",
]


def upgrade() -> None:
    conn = op.get_bind()

    # ------------------------------------------------------------------ #
    # treatment_contexts — convert Text columns to JSON (list of strings) #
    # ------------------------------------------------------------------ #
    for field in CONTEXT_FIELDS:
        # Add a temporary JSON column
        op.add_column(
            "treatment_contexts",
            sa.Column(f"{field}_json", sa.JSON(), nullable=True),
        )

    # Migrate existing data: each non-empty text becomes a single-element list
    result = conn.execute(
        sa.text(
            "SELECT uuid, "
            + ", ".join(CONTEXT_FIELDS)
            + " FROM treatment_contexts"
        )
    )
    rows = result.fetchall()

    for row in rows:
        row_dict = dict(zip(["uuid"] + CONTEXT_FIELDS, row))
        updates = {}
        for field in CONTEXT_FIELDS:
            val = row_dict[field]
            if val and isinstance(val, str) and val.strip():
                # Wrap the existing text as a single-element list
                updates[f"{field}_json"] = [val.strip()]
            else:
                updates[f"{field}_json"] = None

        if updates:
            set_clause = ", ".join(
                f"{k} = :{k}" for k in updates
            )
            params = {k: json.dumps(v) if v is not None else None for k, v in updates.items()}
            conn.execute(
                sa.text(
                    f"UPDATE treatment_contexts SET {set_clause} "
                    f"WHERE uuid = :uuid"
                ),
                {**params, "uuid": str(row_dict["uuid"])},
            )

    # Drop old Text columns and rename JSON columns
    for field in CONTEXT_FIELDS:
        op.drop_column("treatment_contexts", field)
        op.alter_column(
            "treatment_contexts",
            f"{field}_json",
            new_column_name=field,
        )

    # --------------------------------------------------------------------- #
    # treatment_context_drafts — convert Text columns to JSON (diff format)  #
    # Each existing text becomes {"add": [text], "remove": []}               #
    # --------------------------------------------------------------------- #
    for field in CONTEXT_FIELDS:
        op.add_column(
            "treatment_context_drafts",
            sa.Column(f"{field}_json", sa.JSON(), nullable=True),
        )

    result2 = conn.execute(
        sa.text(
            "SELECT uuid, "
            + ", ".join(CONTEXT_FIELDS)
            + " FROM treatment_context_drafts"
        )
    )
    rows2 = result2.fetchall()

    for row in rows2:
        row_dict = dict(zip(["uuid"] + CONTEXT_FIELDS, row))
        updates = {}
        for field in CONTEXT_FIELDS:
            val = row_dict[field]
            if val and isinstance(val, str) and val.strip():
                # Wrap existing draft text as a structured add diff
                updates[f"{field}_json"] = {
                    "add": [val.strip()],
                    "remove": [],
                }
            else:
                updates[f"{field}_json"] = None

        if updates:
            set_clause = ", ".join(
                f"{k} = :{k}" for k in updates
            )
            params = {k: json.dumps(v) if v is not None else None for k, v in updates.items()}
            conn.execute(
                sa.text(
                    f"UPDATE treatment_context_drafts SET {set_clause} "
                    f"WHERE uuid = :uuid"
                ),
                {**params, "uuid": str(row_dict["uuid"])},
            )

    for field in CONTEXT_FIELDS:
        op.drop_column("treatment_context_drafts", field)
        op.alter_column(
            "treatment_context_drafts",
            f"{field}_json",
            new_column_name=field,
        )


def downgrade() -> None:
    conn = op.get_bind()

    # Downgrade: convert JSON columns back to Text
    for field in CONTEXT_FIELDS:
        op.add_column(
            "treatment_contexts",
            sa.Column(f"{field}_text", sa.Text(), nullable=True),
        )

    result = conn.execute(
        sa.text(
            "SELECT uuid, "
            + ", ".join(CONTEXT_FIELDS)
            + " FROM treatment_contexts"
        )
    )
    rows = result.fetchall()

    for row in rows:
        row_dict = dict(zip(["uuid"] + CONTEXT_FIELDS, row))
        updates = {}
        for field in CONTEXT_FIELDS:
            val = row_dict[field]
            if val and isinstance(val, list):
                updates[f"{field}_text"] = "\n".join(
                    f"- {b}" for b in val
                )
            else:
                updates[f"{field}_text"] = None

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                sa.text(
                    f"UPDATE treatment_contexts SET {set_clause} "
                    f"WHERE uuid = :uuid"
                ),
                {**updates, "uuid": str(row_dict["uuid"])},
            )

    for field in CONTEXT_FIELDS:
        op.drop_column("treatment_contexts", field)
        op.alter_column(
            "treatment_contexts",
            f"{field}_text",
            new_column_name=field,
        )

    # Downgrade drafts
    for field in CONTEXT_FIELDS:
        op.add_column(
            "treatment_context_drafts",
            sa.Column(f"{field}_text", sa.Text(), nullable=True),
        )

    result2 = conn.execute(
        sa.text(
            "SELECT uuid, "
            + ", ".join(CONTEXT_FIELDS)
            + " FROM treatment_context_drafts"
        )
    )
    rows2 = result2.fetchall()

    for row in rows2:
        row_dict = dict(zip(["uuid"] + CONTEXT_FIELDS, row))
        updates = {}
        for field in CONTEXT_FIELDS:
            val = row_dict[field]
            if val and isinstance(val, dict):
                add_items = val.get("add", [])
                remove_items = val.get("remove", [])
                parts = []
                if add_items:
                    parts.append(
                        "Adicionar:\n"
                        + "\n".join(f"- {b}" for b in add_items)
                    )
                if remove_items:
                    parts.append(
                        "Remover:\n"
                        + "\n".join(f"- {b}" for b in remove_items)
                    )
                updates[f"{field}_text"] = "\n\n".join(parts) or None
            else:
                updates[f"{field}_text"] = None

        if updates:
            set_clause = ", ".join(f"{k} = :{k}" for k in updates)
            conn.execute(
                sa.text(
                    f"UPDATE treatment_context_drafts SET {set_clause} "
                    f"WHERE uuid = :uuid"
                ),
                {**updates, "uuid": str(row_dict["uuid"])},
            )

    for field in CONTEXT_FIELDS:
        op.drop_column("treatment_context_drafts", field)
        op.alter_column(
            "treatment_context_drafts",
            f"{field}_text",
            new_column_name=field,
        )
