from collections.abc import Callable

from apscheduler.schedulers.blocking import BlockingScheduler

from src.config import settings


def start_scheduler(job: Callable[[], None]) -> None:
    scheduler = BlockingScheduler()

    scheduler.add_job(
        job,
        trigger="interval",
        minutes=settings.check_interval_minutes,
        id="property_listing_search",
        max_instances=1,
        coalesce=True,
    )

    print(
        f"Bot programado cada "
        f"{settings.check_interval_minutes} minutos."
    )
    print("Pulsa Ctrl + C para detenerlo.")

    try:
        scheduler.start()

    except KeyboardInterrupt:
        print("Bot detenido.")