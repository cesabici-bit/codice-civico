"""F10: bitemporal graph layer.

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-17

Introduces the bitemporal identity model:
- persons: stable entity
- person_external_ids: identity claims with per-ID source_url (M5)
- mandates: Person -> Camera/Senato temporal arcs
- party_memberships: Person -> party temporal arcs
- relationships: polymorphic cross-entity temporal arcs

Existing tables (politicians etc.) kept for compat; migration to persons tracked separately.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import BYTEA, UUID

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- persons: stable identity entity ---
    op.create_table(
        "persons",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("primary_full_name", sa.Text(), nullable=False),
        sa.Column("birth_date", sa.Date()),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.execute(
        "CREATE INDEX idx_persons_full_name_trgm ON persons "
        "USING gin (primary_full_name gin_trgm_ops)"
    )

    # --- person_external_ids: M5 per-ID source_url ---
    op.create_table(
        "person_external_ids",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "person_id",
            UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("namespace", sa.String(32), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(64)),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("namespace", "external_id", name="uq_person_ext_id"),
    )
    op.create_index(
        "idx_pei_person", "person_external_ids", ["person_id"],
    )
    op.create_index(
        "idx_pei_lookup", "person_external_ids", ["namespace", "external_id"],
    )

    # --- mandates: Person -> Camera/Senato temporal arc ---
    op.create_table(
        "mandates",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "person_id",
            UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("chamber", sa.String(10), nullable=False),
        sa.Column("legislature", sa.Integer(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("motivo_termine", sa.Text()),
        sa.Column("tipo_mandato", sa.Text()),
        sa.Column("regione_elezione", sa.Text()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(64)),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "chamber IN ('camera','senato')", name="ck_mandate_chamber",
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_mandate_temporal_order",
        ),
        sa.UniqueConstraint(
            "person_id", "chamber", "legislature", "start_date",
            name="uq_mandate_person_leg",
        ),
    )
    op.create_index("idx_mandates_person", "mandates", ["person_id"])
    op.create_index(
        "idx_mandates_temporal", "mandates", ["start_date", "end_date"],
    )

    # --- party_memberships: Person -> party temporal arc ---
    op.create_table(
        "party_memberships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column(
            "person_id",
            UUID(as_uuid=True),
            sa.ForeignKey("persons.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("party", sa.Text(), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("source_checksum", sa.String(64)),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "end_date IS NULL OR end_date >= start_date",
            name="ck_party_temporal_order",
        ),
    )
    op.create_index(
        "idx_party_person", "party_memberships", ["person_id"],
    )
    op.create_index(
        "idx_party_temporal", "party_memberships", ["start_date", "end_date"],
    )

    # --- relationships: polymorphic cross-entity temporal arc ---
    op.create_table(
        "relationships",
        sa.Column(
            "id",
            UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
        ),
        sa.Column("source_id", UUID(as_uuid=True), nullable=False),
        sa.Column("source_type", sa.String(32), nullable=False),
        sa.Column("target_id", UUID(as_uuid=True), nullable=False),
        sa.Column("target_type", sa.String(32), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("valid_from", sa.Date(), nullable=False),
        sa.Column("valid_to", sa.Date()),
        sa.Column("source_url", sa.Text(), nullable=False),
        sa.Column("extraction_method", sa.String(32), nullable=False),
        sa.Column("confidence", sa.Numeric(3, 2), nullable=False),
        sa.Column(
            "ingested_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_checksum", sa.String(64)),
        sa.Column("raw_payload", BYTEA()),
        sa.CheckConstraint(
            "confidence BETWEEN 0 AND 1", name="ck_rel_confidence",
        ),
        sa.CheckConstraint(
            "valid_to IS NULL OR valid_to >= valid_from",
            name="ck_rel_temporal_order",
        ),
    )
    op.create_index("idx_rel_source", "relationships", ["source_id", "source_type"])
    op.create_index("idx_rel_target", "relationships", ["target_id", "target_type"])
    op.create_index("idx_rel_temporal", "relationships", ["valid_from", "valid_to"])
    op.create_index("idx_rel_kind", "relationships", ["kind"])


def downgrade() -> None:
    op.drop_index("idx_rel_kind", table_name="relationships")
    op.drop_index("idx_rel_temporal", table_name="relationships")
    op.drop_index("idx_rel_target", table_name="relationships")
    op.drop_index("idx_rel_source", table_name="relationships")
    op.drop_table("relationships")

    op.drop_index("idx_party_temporal", table_name="party_memberships")
    op.drop_index("idx_party_person", table_name="party_memberships")
    op.drop_table("party_memberships")

    op.drop_index("idx_mandates_temporal", table_name="mandates")
    op.drop_index("idx_mandates_person", table_name="mandates")
    op.drop_table("mandates")

    op.drop_index("idx_pei_lookup", table_name="person_external_ids")
    op.drop_index("idx_pei_person", table_name="person_external_ids")
    op.drop_table("person_external_ids")

    op.execute("DROP INDEX IF EXISTS idx_persons_full_name_trgm")
    op.drop_table("persons")
