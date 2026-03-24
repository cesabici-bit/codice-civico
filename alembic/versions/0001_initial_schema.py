"""Initial schema — all tables, extensions, tribunal seed.

Revision ID: 0001
Revises: (none)
Create Date: 2026-03-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB, UUID


# revision identifiers
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Extensions ---
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')

    # --- Politicians ---
    op.create_table(
        "politicians",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("camera_uri", sa.Text()),
        sa.Column("senato_uri", sa.Text()),
        sa.Column("openpolis_id", sa.Integer()),
        sa.Column("tax_code_hash", sa.Text()),
        sa.Column("current_party", sa.Text()),
        sa.Column("current_chamber", sa.String(10)),
        sa.Column("region", sa.Text()),
        sa.Column("birth_date", sa.Date()),
        sa.Column("photo_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("current_chamber IN ('camera', 'senato', 'ex')"),
    )
    op.execute(
        "CREATE INDEX idx_politicians_name_trgm ON politicians "
        "USING gin (full_name gin_trgm_ops)"
    )

    # --- Legislative Acts ---
    op.create_table(
        "legislative_acts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("act_type", sa.Text()),
        sa.Column("chamber", sa.Text()),
        sa.Column("status", sa.Text()),
        sa.Column("presentation_date", sa.Date()),
        sa.Column("full_text", sa.Text()),
        sa.Column("source_uri", sa.Text()),
        sa.Column("plain_translation", JSONB()),
        sa.Column("translated_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.execute(
        "CREATE INDEX idx_laws_text_trgm ON legislative_acts "
        "USING gin (title gin_trgm_ops)"
    )

    # --- Votes ---
    op.create_table(
        "votes",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("politician_id", UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("subject", sa.Text(), nullable=False),
        sa.Column("vote_value", sa.String(20)),
        sa.Column("legislative_act_id", UUID(as_uuid=True), sa.ForeignKey("legislative_acts.id")),
        sa.Column("source_uri", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("vote_value IN ('favorevole', 'contrario', 'astenuto', 'assente')"),
    )
    op.create_index("idx_votes_politician", "votes", ["politician_id"])
    op.create_index("idx_votes_date", "votes", ["session_date"])

    # --- Speeches ---
    op.create_table(
        "speeches",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("politician_id", UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("speech_date", sa.Date(), nullable=False),
        sa.Column("context", sa.Text()),
        sa.Column("full_text", sa.Text(), nullable=False),
        sa.Column("source_uri", sa.Text()),
        sa.Column("nlp_processed", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # --- Promises ---
    op.create_table(
        "promises",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("politician_id", UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("speech_id", UUID(as_uuid=True), sa.ForeignKey("speeches.id")),
        sa.Column("sentence", sa.Text(), nullable=False),
        sa.Column("topic", sa.Text()),
        sa.Column("specificity_score", sa.Numeric(3, 2)),
        sa.Column("status", sa.String(20), server_default=sa.text("'pending'")),
        sa.Column("confidence", sa.Numeric(3, 2)),
        sa.Column("matched_vote_id", UUID(as_uuid=True), sa.ForeignKey("votes.id")),
        sa.Column("matched_act_id", UUID(as_uuid=True), sa.ForeignKey("legislative_acts.id")),
        sa.Column("match_similarity", sa.Numeric(4, 3)),
        sa.Column("human_verified", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("specificity_score BETWEEN 0 AND 1"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1"),
        sa.CheckConstraint("status IN ('pending', 'kept', 'broken', 'ambiguous')"),
    )

    # --- Contracts ---
    op.create_table(
        "contracts",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("ocid", sa.Text(), unique=True),
        sa.Column("buyer_name", sa.Text(), nullable=False),
        sa.Column("buyer_cf", sa.Text()),
        sa.Column("buyer_region", sa.Text()),
        sa.Column("buyer_province", sa.Text()),
        sa.Column("supplier_name", sa.Text()),
        sa.Column("supplier_cf", sa.Text()),
        sa.Column("cpv_code", sa.Text()),
        sa.Column("amount_awarded", sa.Numeric(15, 2)),
        sa.Column("amount_original", sa.Numeric(15, 2)),
        sa.Column("procedure_type", sa.Text()),
        sa.Column("publication_date", sa.Date()),
        sa.Column("award_date", sa.Date()),
        sa.Column("n_bids", sa.Integer()),
        sa.Column("contract_duration_days", sa.Integer()),
        sa.Column("source_url", sa.Text()),
        sa.Column("risk_score", sa.Numeric(5, 2), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_contracts_buyer", "contracts", ["buyer_cf"])
    op.create_index("idx_contracts_supplier", "contracts", ["supplier_cf"])
    op.create_index("idx_contracts_cpv", "contracts", ["cpv_code"])
    op.create_index("idx_contracts_risk", "contracts", [sa.text("risk_score DESC")])

    # --- Anomaly Flags ---
    op.create_table(
        "anomaly_flags",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("contract_id", UUID(as_uuid=True), sa.ForeignKey("contracts.id"), nullable=False),
        sa.Column("flag_type", sa.Text(), nullable=False),
        sa.Column("severity", sa.String(10)),
        sa.Column("details", JSONB()),
        sa.Column("ml_anomaly_score", sa.Numeric(5, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("severity IN ('low', 'medium', 'high')"),
    )
    op.create_index("idx_anomaly_contract", "anomaly_flags", ["contract_id"])

    # --- Tribunals ---
    op.create_table(
        "tribunals",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("type", sa.String(20)),
        sa.Column("region", sa.Text()),
        sa.Column("province", sa.Text()),
        sa.Column("istat_code", sa.Text()),
        sa.Column("lat", sa.Numeric(9, 6)),
        sa.Column("lon", sa.Numeric(9, 6)),
        sa.CheckConstraint("type IN ('ordinario', 'appello', 'tar', 'corte_conti')"),
    )

    # --- Magistrates ---
    op.create_table(
        "magistrates",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role", sa.String(30)),
        sa.Column("section", sa.Text()),
        sa.Column("tribunal_id", UUID(as_uuid=True), sa.ForeignKey("tribunals.id")),
        sa.Column("csm_id", sa.Text()),
        sa.Column("birth_date", sa.Date()),
        sa.Column("in_office_since", sa.Date()),
        sa.Column("transfer_history", JSONB()),
        sa.Column("disciplinary_records", JSONB()),
        sa.Column("photo_url", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "role IN ('giudice', 'pm', 'presidente', 'procuratore', 'consigliere', 'sostituto')"
        ),
    )
    op.execute(
        "CREATE INDEX idx_magistrates_name_trgm ON magistrates "
        "USING gin (full_name gin_trgm_ops)"
    )

    # --- Magistrate Stats ---
    op.create_table(
        "magistrate_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("magistrate_id", UUID(as_uuid=True), sa.ForeignKey("magistrates.id"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("pending_cases", sa.Integer()),
        sa.Column("new_cases", sa.Integer()),
        sa.Column("resolved_cases", sa.Integer()),
        sa.Column("avg_duration_days", sa.Numeric(8, 2)),
        sa.Column("clearance_rate", sa.Numeric(5, 4)),
        sa.Column("tribunal_avg_duration", sa.Numeric(8, 2)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("magistrate_id", "period"),
    )

    # --- Institutional Figures ---
    op.create_table(
        "institutional_figures",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("full_name", sa.Text(), nullable=False),
        sa.Column("role_type", sa.String(30), nullable=False),
        sa.Column("institution", sa.Text()),
        sa.Column("region", sa.Text()),
        sa.Column("in_office_since", sa.Date()),
        sa.Column("in_office_until", sa.Date()),
        sa.Column("previous_roles", JSONB()),
        sa.Column("linked_contracts_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint(
            "role_type IN ('prefetto', 'dirigente_pa', 'presidente_authority', 'commissario', 'altro')"
        ),
    )
    op.execute(
        "CREATE INDEX idx_instfig_name_trgm ON institutional_figures "
        "USING gin (full_name gin_trgm_ops)"
    )

    # --- Court Stats ---
    op.create_table(
        "court_stats",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("tribunal_id", UUID(as_uuid=True), sa.ForeignKey("tribunals.id"), nullable=False),
        sa.Column("period", sa.Date(), nullable=False),
        sa.Column("case_category", sa.Text()),
        sa.Column("pending_cases", sa.Integer()),
        sa.Column("new_cases", sa.Integer()),
        sa.Column("resolved_cases", sa.Integer()),
        sa.Column("avg_duration_days", sa.Numeric(8, 2)),
        sa.Column("clearance_rate", sa.Numeric(5, 4)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("tribunal_id", "period", "case_category"),
    )

    # --- Asset Declarations ---
    op.create_table(
        "asset_declarations",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("politician_id", UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("declaration_year", sa.Integer(), nullable=False),
        sa.Column("total_income", sa.Numeric(15, 2)),
        sa.Column("total_assets", sa.Numeric(15, 2)),
        sa.Column("real_estate_count", sa.Integer()),
        sa.Column("company_participations", JSONB()),
        sa.Column("source_pdf_url", sa.Text()),
        sa.Column("raw_text", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("politician_id", "declaration_year"),
    )

    # --- Entity Links ---
    op.create_table(
        "entity_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("uuid_generate_v4()")),
        sa.Column("politician_id", UUID(as_uuid=True), sa.ForeignKey("politicians.id"), nullable=False),
        sa.Column("entity_type", sa.String(20), nullable=False),
        sa.Column("entity_identifier", sa.Text()),
        sa.Column("link_type", sa.Text()),
        sa.Column("confidence", sa.Numeric(3, 2)),
        sa.Column("source", sa.Text()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.CheckConstraint("entity_type IN ('supplier', 'buyer', 'company')"),
    )

    # --- Ingestion Log ---
    op.create_table(
        "ingestion_log",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("source_name", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("status", sa.String(10)),
        sa.Column("records_processed", sa.Integer(), server_default=sa.text("0")),
        sa.Column("errors", JSONB()),
        sa.Column("checkpoint_value", sa.Text()),
        sa.CheckConstraint("status IN ('running', 'success', 'failed')"),
    )

    # --- Seed Tribunals ---
    _seed_tribunals()


def _seed_tribunals() -> None:
    """Seed the 140+ Italian tribunals."""
    from codicecivico.ingest.tribunali_seed import TRIBUNALI

    tribunals_table = sa.table(
        "tribunals",
        sa.column("name", sa.Text),
        sa.column("type", sa.String),
        sa.column("region", sa.Text),
        sa.column("province", sa.Text),
        sa.column("lat", sa.Numeric),
        sa.column("lon", sa.Numeric),
    )
    rows = [
        {
            "name": t["name"],
            "type": "ordinario",
            "region": t["region"],
            "province": t["province"],
            "lat": t["lat"],
            "lon": t["lon"],
        }
        for t in TRIBUNALI
    ]
    if rows:
        op.bulk_insert(tribunals_table, rows)


def downgrade() -> None:
    tables = [
        "ingestion_log", "entity_links", "asset_declarations", "court_stats",
        "institutional_figures", "magistrate_stats", "magistrates", "tribunals",
        "anomaly_flags", "contracts", "promises", "speeches", "votes",
        "legislative_acts", "politicians",
    ]
    for table in tables:
        op.drop_table(table)
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
