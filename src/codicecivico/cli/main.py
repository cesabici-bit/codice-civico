"""CLI entrypoint for Codice Civico operations."""

import asyncio
import logging

import click

from codicecivico.db import async_session


def _run_async(coro):  # type: ignore[no-untyped-def]
    """Run an async coroutine from sync CLI context."""
    return asyncio.run(coro)


@click.group()
@click.option("-v", "--verbose", is_flag=True, help="Enable debug logging.")
def cli(verbose: bool) -> None:
    """Codice Civico — AI-powered civic accountability engine."""
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(name)s %(levelname)s %(message)s",
    )


@cli.command()
@click.option(
    "--source",
    type=click.Choice(["camera", "senato", "openpolis", "anac", "giustizia", "assets"]),
    required=True,
)
@click.option("--limit", type=int, default=None, help="Max pages/records (for testing).")
@click.option("--year", type=int, default=None, help="Year for ANAC ingestion.")
@click.option("--month", type=int, default=None, help="Month for ANAC ingestion.")
def ingest(source: str, limit: int | None, year: int | None, month: int | None) -> None:
    """Run data ingestion for a specific source."""
    from codicecivico.ingest.anac import AnacIngestor
    from codicecivico.ingest.camera import CameraIngestor
    from codicecivico.ingest.giustizia import GiustiziaIngestor
    from codicecivico.ingest.senato import SenatoIngestor

    ingestors: dict[str, type] = {
        "camera": CameraIngestor,
        "senato": SenatoIngestor,
        "anac": AnacIngestor,
        "giustizia": GiustiziaIngestor,
    }

    cls = ingestors.get(source)
    if cls is None:
        click.echo(f"Ingestion for '{source}' not yet implemented.")
        return

    async def _run() -> int:
        async with async_session() as session:
            ingestor = cls()
            if source == "anac":
                result: int = await ingestor.ingest(
                    session, limit=limit, year=year, month=month,
                )
                return result
            result = await ingestor.ingest(session, limit=limit)
            return result

    total = _run_async(_run())
    click.echo(f"[{source}] Ingestion complete: {total} records processed.")


@cli.command("decode-entities")
def decode_entities() -> None:
    """Backfill clean_text across rows that contain HTML entities or tags.

    One-shot migration for data ingested before the clean_text helper was
    added. Operates on legislative_acts.title and speeches.full_text.
    Idempotent: rows already clean are left untouched.
    """
    from sqlalchemy import or_, select

    from codicecivico.ingest.base import clean_text
    from codicecivico.models import LegislativeAct, Speech

    async def _run() -> tuple[int, int]:
        laws_updated = 0
        speeches_updated = 0
        async with async_session() as session:
            stmt = select(LegislativeAct).where(
                or_(
                    LegislativeAct.title.like("%&%"),
                    LegislativeAct.title.like("%<%"),
                ),
            )
            result = await session.execute(stmt)
            for law in result.scalars().all():
                cleaned = clean_text(law.title)
                if cleaned and cleaned != law.title:
                    law.title = cleaned[:2000]
                    laws_updated += 1

            stmt2 = select(Speech).where(
                or_(
                    Speech.full_text.like("%&%"),
                    Speech.full_text.like("%<%"),
                ),
            )
            result2 = await session.execute(stmt2)
            for sp in result2.scalars().all():
                cleaned = clean_text(sp.full_text)
                if cleaned and cleaned != sp.full_text:
                    sp.full_text = cleaned
                    speeches_updated += 1

            await session.commit()
        return laws_updated, speeches_updated

    laws, speeches = _run_async(_run())
    click.echo(
        f"[decode-entities] Cleaned {laws} laws and {speeches} speeches.",
    )


@cli.command("anac-awards")
@click.option(
    "--snapshot",
    required=True,
    help="Aggiudicazioni snapshot date YYYYMMDD (e.g. 20260401).",
)
def anac_awards(snapshot: str) -> None:
    """Update contracts with amount_awarded / award_date / n_bids.

    Streams the `aggiudicazioni` dataset (distinct from `aggiudicatari`)
    and fills NULL fields on existing Contract rows. Idempotent.
    """
    from codicecivico.ingest.anac import AnacIngestor

    async def _run() -> int:
        async with async_session() as session:
            ingestor = AnacIngestor()
            return await ingestor.update_awards_from_snapshot(
                session, snapshot_date=snapshot,
            )

    total = _run_async(_run())
    click.echo(f"[anac-awards] Updated {total} contracts with award info.")


@cli.command("anac-suppliers")
@click.option(
    "--snapshot",
    required=True,
    help="Aggiudicatari snapshot date in YYYYMMDD format (e.g. 20260401).",
)
def anac_suppliers(snapshot: str) -> None:
    """Update existing contracts with supplier_name/supplier_cf from aggiudicatari.

    Streams the aggiudicatari CSV from ANAC (cumulative, ~99MB uncompressed)
    and fills in supplier info on Contract rows already ingested via
    `ingest --source anac`. Idempotent: only updates rows where
    supplier_name is NULL.
    """
    from codicecivico.ingest.anac import AnacIngestor

    async def _run() -> int:
        async with async_session() as session:
            ingestor = AnacIngestor()
            return await ingestor.update_suppliers_from_snapshot(
                session, snapshot_date=snapshot,
            )

    total = _run_async(_run())
    click.echo(f"[anac-suppliers] Updated {total} contracts with supplier info.")


@cli.command("entity-resolve")
def entity_resolve() -> None:
    """Run cross-chamber entity resolution (merge Camera/Senato duplicates)."""
    from codicecivico.entity.resolver import merge_cross_chamber

    async def _run() -> int:
        async with async_session() as session:
            count = await merge_cross_chamber(session)
            await session.commit()
            return count

    merged = _run_async(_run())
    click.echo(f"Entity resolution complete: {merged} cross-chamber merges.")


@cli.command()
@click.option(
    "--pipeline",
    type=click.Choice(["promises"]),
    required=True,
    help="NLP pipeline to run.",
)
@click.option("--limit", type=int, default=None, help="Max speeches to process.")
def nlp(pipeline: str, limit: int | None) -> None:
    """Run NLP pipelines on ingested data."""
    from codicecivico.nlp.pipeline import run_promise_pipeline

    async def _run() -> int:
        async with async_session() as session:
            count = await run_promise_pipeline(session, limit=limit)
            await session.commit()
            return count

    total = _run_async(_run())
    click.echo(f"[{pipeline}] NLP pipeline complete: {total} promises extracted.")


@cli.command()
@click.option("--model", type=click.Choice(["anomaly"]), required=True)
@click.option("--limit", type=int, default=None, help="Max contracts to score.")
def train(model: str, limit: int | None) -> None:
    """Run anomaly detection pipeline on ingested contracts.

    Loads all Contract rows, trains IsolationForest, runs 7 rule-based
    checks, and populates AnomalyFlag + Contract.risk_score.
    Idempotent: clears existing flags before recomputing.
    """
    from codicecivico.anomaly.pipeline import run_anomaly_pipeline

    async def _run() -> tuple[int, int]:
        async with async_session() as session:
            scored, flags = await run_anomaly_pipeline(session, limit=limit)
            await session.commit()
            return scored, flags

    scored, flags = _run_async(_run())
    click.echo(
        f"[{model}] Pipeline complete: {scored} contracts scored, "
        f"{flags} AnomalyFlag rows inserted.",
    )


@cli.command()
@click.option("--law-id", required=True, help="UUID of the legislative act to translate.")
@click.option("--force", is_flag=True, help="Re-translate even if already translated.")
@click.option("--max-articles", type=int, default=None, help="Max articles to translate.")
def translate(law_id: str, force: bool, max_articles: int | None) -> None:
    """Translate a legislative act to plain Italian via local LLM (Ollama)."""
    import json
    import uuid as uuid_mod

    from sqlalchemy import select

    from codicecivico.models import LegislativeAct
    from codicecivico.nlp.translator import translate_law

    try:
        law_uuid = uuid_mod.UUID(law_id)
    except ValueError:
        click.echo(f"Error: '{law_id}' is not a valid UUID.", err=True)
        raise SystemExit(1)

    async def _run() -> dict | None:
        async with async_session() as session:
            result = await session.execute(
                select(LegislativeAct).where(LegislativeAct.id == law_uuid),
            )
            law = result.scalar_one_or_none()
            if law is None:
                click.echo(f"Error: law {law_id} not found.", err=True)
                raise SystemExit(1)

            if law.plain_translation and not force:
                click.echo("Law already translated (use --force to re-translate).")
                return law.plain_translation  # type: ignore[return-value]

            if not law.full_text:
                click.echo("Error: law has no full text to translate.", err=True)
                raise SystemExit(1)

            translation = await translate_law(
                law.full_text,
                max_articles=max_articles,
            )
            if translation is None:
                click.echo(
                    "Error: Ollama not available. Start it with 'ollama serve'.",
                    err=True,
                )
                raise SystemExit(1)

            # Persist
            from datetime import datetime, timezone

            law.plain_translation = translation
            law.translated_at = datetime.now(timezone.utc)
            await session.commit()
            return translation  # type: ignore[return-value]

    result = _run_async(_run())
    if result:
        click.echo(json.dumps(result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    cli()
