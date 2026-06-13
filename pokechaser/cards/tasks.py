import logging

from celery import shared_task

from pokechaser.cards.utils import CardApi

logger = logging.getLogger(__name__)


@shared_task
def sync_pokemon_cards():
    logger.info("Starting scheduled Pokemon TCG API sync")
    stats = CardApi().run()
    logger.info("Scheduled sync complete: %s", stats)
    return stats
