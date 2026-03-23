"""APScheduler configuration for periodic data ingestion."""


def setup_scheduler() -> None:
    """Configure and start the ingestion scheduler.

    Schedule:
    - Camera: daily at 02:00 UTC
    - Senato: daily at 02:30 UTC
    - Openpolis: weekly Sunday 03:00 UTC
    - ANAC: monthly 1st at 04:00 UTC
    - Giustizia: monthly 1st at 04:30 UTC
    """
    raise NotImplementedError("Scheduler not yet implemented (F2)")
