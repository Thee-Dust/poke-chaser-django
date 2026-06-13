from django.core.management.base import BaseCommand

from pokechaser.cards.utils import CardApi


class Command(BaseCommand):
    help = "Fetch sets and cards from the Pokemon TCG API and upsert them into the database."

    def handle(self, *args, **options):
        self.stdout.write("Starting Pokemon TCG API sync...")
        stats = CardApi().run()
        self.stdout.write(
            self.style.SUCCESS(
                "Sync complete: "
                f"sets created={stats['sets_created']} updated={stats['sets_updated']}, "
                f"cards created={stats['cards_created']} updated={stats['cards_updated']} "
                f"skipped={stats['cards_skipped']}"
            )
        )
