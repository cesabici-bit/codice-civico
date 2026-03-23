"""SQLAlchemy ORM models for Codice Civico."""

import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    """Base class for all ORM models."""


# ---------------------------------------------------------------------------
# Politicians (unified across Camera + Senato)
# ---------------------------------------------------------------------------


class Politician(Base):
    __tablename__ = "politicians"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    camera_uri: Mapped[str | None] = mapped_column(Text)
    senato_uri: Mapped[str | None] = mapped_column(Text)
    openpolis_id: Mapped[int | None] = mapped_column(Integer)
    tax_code_hash: Mapped[str | None] = mapped_column(Text)
    current_party: Mapped[str | None] = mapped_column(Text)
    current_chamber: Mapped[str | None] = mapped_column(
        String(10),
        CheckConstraint("current_chamber IN ('camera', 'senato', 'ex')"),
    )
    region: Mapped[str | None] = mapped_column(Text)
    birth_date: Mapped[date | None] = mapped_column(Date)
    photo_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    votes: Mapped[list["Vote"]] = relationship(back_populates="politician")
    speeches: Mapped[list["Speech"]] = relationship(back_populates="politician")
    promises: Mapped[list["Promise"]] = relationship(back_populates="politician")
    asset_declarations: Mapped[list["AssetDeclaration"]] = relationship(
        back_populates="politician",
    )
    entity_links: Mapped[list["EntityLink"]] = relationship(back_populates="politician")

    __table_args__ = (
        Index("idx_politicians_name_trgm", "full_name", postgresql_using="gin",
              postgresql_ops={"full_name": "gin_trgm_ops"}),
    )


# ---------------------------------------------------------------------------
# Legislative Acts
# ---------------------------------------------------------------------------


class LegislativeAct(Base):
    __tablename__ = "legislative_acts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    act_type: Mapped[str | None] = mapped_column(Text)  # DDL, DL, legge, decreto
    chamber: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)  # presentato, in commissione, approvato
    presentation_date: Mapped[date | None] = mapped_column(Date)
    full_text: Mapped[str | None] = mapped_column(Text)
    source_uri: Mapped[str | None] = mapped_column(Text)
    plain_translation: Mapped[dict | None] = mapped_column(JSONB)
    translated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    votes: Mapped[list["Vote"]] = relationship(back_populates="legislative_act")

    __table_args__ = (
        Index("idx_laws_text_trgm", "title", postgresql_using="gin",
              postgresql_ops={"title": "gin_trgm_ops"}),
    )


# ---------------------------------------------------------------------------
# Votes
# ---------------------------------------------------------------------------


class Vote(Base):
    __tablename__ = "votes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"), nullable=False)
    session_date: Mapped[date] = mapped_column(Date, nullable=False)
    subject: Mapped[str] = mapped_column(Text, nullable=False)
    vote_value: Mapped[str | None] = mapped_column(
        String(20),
        CheckConstraint("vote_value IN ('favorevole', 'contrario', 'astenuto', 'assente')"),
    )
    legislative_act_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("legislative_acts.id"))
    source_uri: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(back_populates="votes")
    legislative_act: Mapped["LegislativeAct | None"] = relationship(back_populates="votes")

    __table_args__ = (
        Index("idx_votes_politician", "politician_id"),
        Index("idx_votes_date", "session_date"),
    )


# ---------------------------------------------------------------------------
# Speeches
# ---------------------------------------------------------------------------


class Speech(Base):
    __tablename__ = "speeches"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"), nullable=False)
    speech_date: Mapped[date] = mapped_column(Date, nullable=False)
    context: Mapped[str | None] = mapped_column(Text)  # e.g. "Aula", "Commissione Bilancio"
    full_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_uri: Mapped[str | None] = mapped_column(Text)
    nlp_processed: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(back_populates="speeches")
    promises: Mapped[list["Promise"]] = relationship(back_populates="speech")


# ---------------------------------------------------------------------------
# Promises (NLP-extracted)
# ---------------------------------------------------------------------------


class Promise(Base):
    __tablename__ = "promises"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"), nullable=False)
    speech_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("speeches.id"))
    sentence: Mapped[str] = mapped_column(Text, nullable=False)
    topic: Mapped[str | None] = mapped_column(Text)
    specificity_score: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        CheckConstraint("specificity_score BETWEEN 0 AND 1"),
    )
    status: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("status IN ('pending', 'kept', 'broken', 'ambiguous')"),
        default="pending",
    )
    # Note: embedding vector(384) requires pgvector extension — added via migration
    confidence: Mapped[float | None] = mapped_column(
        Numeric(3, 2),
        CheckConstraint("confidence BETWEEN 0 AND 1"),
    )
    matched_vote_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("votes.id"))
    matched_act_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("legislative_acts.id"),
    )
    match_similarity: Mapped[float | None] = mapped_column(Numeric(4, 3))
    human_verified: Mapped[bool] = mapped_column(default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(back_populates="promises")
    speech: Mapped["Speech | None"] = relationship(back_populates="promises")
    matched_act: Mapped["LegislativeAct | None"] = relationship()


# ---------------------------------------------------------------------------
# Contracts (ANAC/OCDS)
# ---------------------------------------------------------------------------


class Contract(Base):
    __tablename__ = "contracts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ocid: Mapped[str | None] = mapped_column(Text, unique=True)
    buyer_name: Mapped[str] = mapped_column(Text, nullable=False)
    buyer_cf: Mapped[str | None] = mapped_column(Text)
    buyer_region: Mapped[str | None] = mapped_column(Text)
    buyer_province: Mapped[str | None] = mapped_column(Text)
    supplier_name: Mapped[str | None] = mapped_column(Text)
    supplier_cf: Mapped[str | None] = mapped_column(Text)
    cpv_code: Mapped[str | None] = mapped_column(Text)
    amount_awarded: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    amount_original: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    procedure_type: Mapped[str | None] = mapped_column(Text)
    publication_date: Mapped[date | None] = mapped_column(Date)
    award_date: Mapped[date | None] = mapped_column(Date)
    n_bids: Mapped[int | None] = mapped_column(Integer)
    contract_duration_days: Mapped[int | None] = mapped_column(Integer)
    source_url: Mapped[str | None] = mapped_column(Text)
    risk_score: Mapped[float] = mapped_column(Numeric(5, 2), default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    anomaly_flags: Mapped[list["AnomalyFlag"]] = relationship(back_populates="contract")

    __table_args__ = (
        Index("idx_contracts_buyer", "buyer_cf"),
        Index("idx_contracts_supplier", "supplier_cf"),
        Index("idx_contracts_cpv", "cpv_code"),
        Index("idx_contracts_risk", risk_score.desc()),
    )


# ---------------------------------------------------------------------------
# Anomaly Flags
# ---------------------------------------------------------------------------


class AnomalyFlag(Base):
    __tablename__ = "anomaly_flags"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    contract_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contracts.id"), nullable=False)
    flag_type: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str | None] = mapped_column(
        String(10),
        CheckConstraint("severity IN ('low', 'medium', 'high')"),
    )
    details: Mapped[dict | None] = mapped_column(JSONB)
    ml_anomaly_score: Mapped[float | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    contract: Mapped["Contract"] = relationship(back_populates="anomaly_flags")

    __table_args__ = (
        Index("idx_anomaly_contract", "contract_id"),
    )


# ---------------------------------------------------------------------------
# Tribunals
# ---------------------------------------------------------------------------


class Tribunal(Base):
    __tablename__ = "tribunals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    type: Mapped[str | None] = mapped_column(
        String(20),
        CheckConstraint("type IN ('ordinario', 'appello', 'tar', 'corte_conti')"),
    )
    region: Mapped[str | None] = mapped_column(Text)
    province: Mapped[str | None] = mapped_column(Text)
    istat_code: Mapped[str | None] = mapped_column(Text)
    lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    lon: Mapped[float | None] = mapped_column(Numeric(9, 6))

    # Relationships
    stats: Mapped[list["CourtStat"]] = relationship(back_populates="tribunal")
    magistrates: Mapped[list["Magistrate"]] = relationship(
        back_populates="tribunal",
    )


# ---------------------------------------------------------------------------
# Magistrates (judges, prosecutors)
# ---------------------------------------------------------------------------


class Magistrate(Base):
    __tablename__ = "magistrates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str | None] = mapped_column(
        String(30),
        CheckConstraint(
            "role IN ('giudice', 'pm', 'presidente', "
            "'procuratore', 'consigliere', 'sostituto')"
        ),
    )
    section: Mapped[str | None] = mapped_column(Text)  # sezione civile, penale
    tribunal_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("tribunals.id"),
    )
    csm_id: Mapped[str | None] = mapped_column(Text)  # CSM identifier
    birth_date: Mapped[date | None] = mapped_column(Date)
    in_office_since: Mapped[date | None] = mapped_column(Date)
    transfer_history: Mapped[dict | None] = mapped_column(JSONB)
    disciplinary_records: Mapped[dict | None] = mapped_column(JSONB)
    photo_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow,
    )

    # Relationships
    tribunal: Mapped["Tribunal | None"] = relationship(
        back_populates="magistrates",
    )
    stats: Mapped[list["MagistrateStat"]] = relationship(
        back_populates="magistrate",
    )

    __table_args__ = (
        Index(
            "idx_magistrates_name_trgm", "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )


class MagistrateStat(Base):
    __tablename__ = "magistrate_stats"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    magistrate_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("magistrates.id"), nullable=False,
    )
    period: Mapped[date] = mapped_column(Date, nullable=False)
    pending_cases: Mapped[int | None] = mapped_column(Integer)
    new_cases: Mapped[int | None] = mapped_column(Integer)
    resolved_cases: Mapped[int | None] = mapped_column(Integer)
    avg_duration_days: Mapped[float | None] = mapped_column(Numeric(8, 2))
    clearance_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    tribunal_avg_duration: Mapped[float | None] = mapped_column(
        Numeric(8, 2),
    )  # for comparison
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow,
    )

    # Relationships
    magistrate: Mapped["Magistrate"] = relationship(
        back_populates="stats",
    )

    __table_args__ = (
        UniqueConstraint("magistrate_id", "period"),
    )


# ---------------------------------------------------------------------------
# Institutional Figures (prefects, PA directors, authority presidents)
# ---------------------------------------------------------------------------


class InstitutionalFigure(Base):
    __tablename__ = "institutional_figures"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4,
    )
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role_type: Mapped[str] = mapped_column(
        String(30),
        CheckConstraint(
            "role_type IN ('prefetto', 'dirigente_pa', "
            "'presidente_authority', 'commissario', 'altro')"
        ),
        nullable=False,
    )
    institution: Mapped[str | None] = mapped_column(Text)
    region: Mapped[str | None] = mapped_column(Text)
    in_office_since: Mapped[date | None] = mapped_column(Date)
    in_office_until: Mapped[date | None] = mapped_column(Date)
    previous_roles: Mapped[dict | None] = mapped_column(JSONB)
    linked_contracts_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=datetime.utcnow,
    )

    __table_args__ = (
        Index(
            "idx_instfig_name_trgm", "full_name",
            postgresql_using="gin",
            postgresql_ops={"full_name": "gin_trgm_ops"},
        ),
    )


# ---------------------------------------------------------------------------
# Court Statistics (time series)
# ---------------------------------------------------------------------------


class CourtStat(Base):
    __tablename__ = "court_stats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tribunal_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tribunals.id"), nullable=False)
    period: Mapped[date] = mapped_column(Date, nullable=False)
    case_category: Mapped[str | None] = mapped_column(Text)  # civile, penale, lavoro
    pending_cases: Mapped[int | None] = mapped_column(Integer)
    new_cases: Mapped[int | None] = mapped_column(Integer)
    resolved_cases: Mapped[int | None] = mapped_column(Integer)
    avg_duration_days: Mapped[float | None] = mapped_column(Numeric(8, 2))
    clearance_rate: Mapped[float | None] = mapped_column(Numeric(5, 4))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    tribunal: Mapped["Tribunal"] = relationship(back_populates="stats")

    __table_args__ = (
        UniqueConstraint("tribunal_id", "period", "case_category"),
    )


# ---------------------------------------------------------------------------
# Asset Declarations
# ---------------------------------------------------------------------------


class AssetDeclaration(Base):
    __tablename__ = "asset_declarations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"), nullable=False)
    declaration_year: Mapped[int] = mapped_column(Integer, nullable=False)
    total_income: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    total_assets: Mapped[Decimal | None] = mapped_column(Numeric(15, 2))
    real_estate_count: Mapped[int | None] = mapped_column(Integer)
    company_participations: Mapped[dict | None] = mapped_column(JSONB)
    source_pdf_url: Mapped[str | None] = mapped_column(Text)
    raw_text: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(back_populates="asset_declarations")

    __table_args__ = (
        UniqueConstraint("politician_id", "declaration_year"),
    )


# ---------------------------------------------------------------------------
# Entity cross-references (politician <-> supplier/buyer)
# ---------------------------------------------------------------------------


class EntityLink(Base):
    __tablename__ = "entity_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    politician_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("politicians.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(
        String(20),
        CheckConstraint("entity_type IN ('supplier', 'buyer', 'company')"),
        nullable=False,
    )
    entity_identifier: Mapped[str | None] = mapped_column(Text)
    link_type: Mapped[str | None] = mapped_column(Text)  # shareholder, board_member, family
    confidence: Mapped[float | None] = mapped_column(Numeric(3, 2))
    source: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    politician: Mapped["Politician"] = relationship(back_populates="entity_links")


# ---------------------------------------------------------------------------
# Ingestion Log
# ---------------------------------------------------------------------------


class IngestionLog(Base):
    __tablename__ = "ingestion_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_name: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str | None] = mapped_column(
        String(10),
        CheckConstraint("status IN ('running', 'success', 'failed')"),
    )
    records_processed: Mapped[int] = mapped_column(Integer, default=0)
    errors: Mapped[dict | None] = mapped_column(JSONB)
    checkpoint_value: Mapped[str | None] = mapped_column(Text)
