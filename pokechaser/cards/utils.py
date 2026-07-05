import logging
import os
import time
from datetime import datetime

import requests
from django.db import transaction
from django.utils import timezone

from pokechaser.cards.models import Card, CardSet

logger = logging.getLogger(__name__)


# --- API field mapping ---


def _normalize_api_date_parts(value):
    date_part, _, time_part = value.partition(" ")
    parts = date_part.split("/")
    if len(parts) != 3:
        raise ValueError(f"unexpected date format: {value!r}")
    year, month, day = parts
    return f"{int(year):04d}/{int(month):02d}/{int(day):02d}", time_part


def parse_release_date(value):
    if not value:
        return None
    try:
        date_part, _ = _normalize_api_date_parts(value)
        return datetime.strptime(date_part, "%Y/%m/%d").date()
    except ValueError:
        logger.warning("Could not parse releaseDate: %s", value)
        return None


def parse_updated_at(value):
    if not value:
        return None
    try:
        date_part, time_part = _normalize_api_date_parts(value)
        if not time_part:
            time_part = "00:00:00"
        parsed = datetime.strptime(f"{date_part} {time_part}", "%Y/%m/%d %H:%M:%S")
    except ValueError:
        logger.warning("Could not parse updatedAt: %s", value)
        return None
    return timezone.make_aware(parsed, timezone.get_current_timezone())


def map_set(data):
    return {
        "name": data["name"],
        "series": data["series"],
        "printed_total": data["printedTotal"],
        "total": data["total"],
        "ptcgo_code": data.get("ptcgoCode", "") or "",
        "release_date": parse_release_date(data.get("releaseDate")),
        "updated_at_api": parse_updated_at(data.get("updatedAt")),
        "legalities": data.get("legalities", {}),
        "images": data.get("images", {}),
    }


def map_card(data):
    return {
        "name": data["name"],
        "supertype": data["supertype"],
        "subtypes": data.get("subtypes", []),
        "level": data.get("level", "") or "",
        "hp": data.get("hp", "") or "",
        "types": data.get("types", []),
        "evolves_from": data.get("evolvesFrom", "") or "",
        "evolves_to": data.get("evolvesTo", []),
        "rules": data.get("rules", []),
        "ancient_trait": data.get("ancientTrait"),
        "abilities": data.get("abilities", []),
        "attacks": data.get("attacks", []),
        "weaknesses": data.get("weaknesses", []),
        "resistances": data.get("resistances", []),
        "retreat_cost": data.get("retreatCost", []),
        "converted_retreat_cost": data.get("convertedRetreatCost"),
        "number": data["number"],
        "artist": data.get("artist", "") or "",
        "rarity": data.get("rarity", "") or "",
        "regulation_mark": data.get("regulationMark", "") or "",
        "flavor_text": data.get("flavorText", "") or "",
        "national_pokedex_numbers": data.get("nationalPokedexNumbers", []),
        "legalities": data.get("legalities", {}),
        "images": data.get("images", {}),
        "tcgplayer": data.get("tcgplayer"),
        "cardmarket": data.get("cardmarket"),
    }


# --- HTTP client ---


class CardApi:
    base_url = "https://api.pokemontcg.io/v2"
    page_size = 250
    max_retries = 5
    set_max_retries = 3
    page_delay_seconds = 1
    set_delay_seconds = 0.5

    def _request(self, url, params=None):
        api_key = os.getenv("POKEMON_TCG_API_KEY", "")
        headers = {}
        if api_key:
            headers["X-Api-Key"] = api_key

        attempt = 1
        while attempt <= self.max_retries:
            try:
                response = requests.get(
                    url,
                    params=params,
                    headers=headers,
                    timeout=60,
                )
            except requests.RequestException as exc:
                if attempt == self.max_retries:
                    raise RuntimeError(f"Request failed after {attempt} attempts: {exc}") from exc
                wait = 2 ** attempt
                logger.warning("Request error (attempt %s/%s): %s", attempt, self.max_retries, exc)
                time.sleep(wait)
                attempt += 1
                continue

            if response.status_code in (404, 429) or response.status_code >= 500:
                if attempt == self.max_retries:
                    response.raise_for_status()
                wait = 2 ** attempt
                logger.warning(
                    "Retryable status %s (attempt %s/%s), waiting %ss",
                    response.status_code,
                    attempt,
                    self.max_retries,
                    wait,
                )
                time.sleep(wait)
                attempt += 1
                continue

            response.raise_for_status()
            return response.json()

        raise RuntimeError(f"Request failed after {self.max_retries} attempts")

    def _paginate(self, endpoint, extra_params=None):
        url = f"{self.base_url}/{endpoint}"
        page = 1
        results = []
        seen_ids = set()
        query_params = extra_params or {}
        total_pages = 1

        while True:
            params = {
                "page": page,
                "pageSize": self.page_size,
                "orderBy": "id",
                **query_params,
            }
            payload = self._request(url, params=params)
            batch = payload.get("data", [])

            for item in batch:
                item_id = item.get("id")
                if item_id and item_id in seen_ids:
                    logger.warning(
                        "Duplicate %s id %s on page %s, skipping",
                        endpoint,
                        item_id,
                        page,
                    )
                    continue
                if item_id:
                    seen_ids.add(item_id)
                results.append(item)

            total_count = payload.get("totalCount", 0)
            total_pages = max(1, (total_count + self.page_size - 1) // self.page_size)
            logger.info(
                "Fetching %s: page %s/%s (%s items so far)",
                endpoint,
                page,
                total_pages,
                len(results),
            )

            if page * self.page_size >= total_count or not batch:
                break

            page += 1
            time.sleep(self.page_delay_seconds)

        return results

    # --- Sync orchestration ---

    def run(self):
        stats = self._empty_stats()
        sets_failed = []

        logger.info("Starting sync: fetching sets...")
        sets = self._fetch_sets()
        set_stats = self._save_sets(sets)
        self._merge_stats(stats, set_stats)

        total_sets = len(sets)
        logger.info("Starting sync: fetching cards for %s sets...", total_sets)

        for index, set_data in enumerate(sets, start=1):
            set_id = set_data["id"]
            try:
                card_stats = self._sync_set(set_data, index, total_sets)
                self._merge_stats(stats, card_stats)
            except Exception:
                logger.exception("Failed to sync set %s after %s attempts", set_id, self.set_max_retries)
                sets_failed.append(set_id)

            if index < total_sets:
                time.sleep(self.set_delay_seconds)

        logger.info(
            "Sync complete: sets created=%s updated=%s, cards created=%s updated=%s skipped=%s, sets_failed=%s",
            stats["sets_created"],
            stats["sets_updated"],
            stats["cards_created"],
            stats["cards_updated"],
            stats["cards_skipped"],
            sets_failed,
        )

        if sets_failed:
            raise RuntimeError(f"Sync failed for sets: {sets_failed}")

        return stats

    def _sync_set(self, set_data, index, total_sets):
        set_id = set_data["id"]
        last_exc = None

        for attempt in range(1, self.set_max_retries + 1):
            try:
                cards = self._fetch_cards_for_set(set_id)
                card_stats = self._save_cards(set_id, cards)
                logger.info(
                    "Set %s/%s: %s — %s cards (created=%s updated=%s skipped=%s)",
                    index,
                    total_sets,
                    set_id,
                    len(cards),
                    card_stats["cards_created"],
                    card_stats["cards_updated"],
                    card_stats["cards_skipped"],
                )
                return card_stats
            except Exception as exc:
                last_exc = exc
                if attempt < self.set_max_retries:
                    wait = 2 ** attempt
                    logger.warning(
                        "Set %s sync failed (attempt %s/%s): %s — retrying in %ss",
                        set_id,
                        attempt,
                        self.set_max_retries,
                        exc,
                        wait,
                    )
                    time.sleep(wait)

        raise last_exc

    def _fetch_sets(self):
        sets = self._paginate("sets")
        logger.info("Finished fetching %s sets from API", len(sets))
        return sets

    def _fetch_cards_for_set(self, set_id):
        return self._paginate("cards", extra_params={"q": f"set.id:{set_id}"})

    def _empty_stats(self):
        return {
            "sets_created": 0,
            "sets_updated": 0,
            "cards_created": 0,
            "cards_updated": 0,
            "cards_skipped": 0,
        }

    def _merge_stats(self, total, partial):
        for key, value in partial.items():
            total[key] = total.get(key, 0) + value

    def _save_sets(self, sets):
        stats = self._empty_stats()

        with transaction.atomic():
            logger.info("Saving %s sets...", len(sets))
            for set_data in sets:
                _, created = CardSet.objects.update_or_create(
                    id=set_data["id"],
                    defaults=map_set(set_data),
                )
                if created:
                    stats["sets_created"] += 1
                else:
                    stats["sets_updated"] += 1

        return stats

    def _save_cards(self, set_id, cards):
        stats = self._empty_stats()

        if not CardSet.objects.filter(id=set_id).exists():
            stats["cards_skipped"] += len(cards)
            logger.warning("Skipping %s cards: set %s not in database", len(cards), set_id)
            return stats

        with transaction.atomic():
            for card_data in cards:
                card_set_id = card_data.get("set", {}).get("id")
                if card_set_id != set_id:
                    stats["cards_skipped"] += 1
                    logger.warning(
                        "Skipping card %s: expected set %s, got %s",
                        card_data.get("id"),
                        set_id,
                        card_set_id,
                    )
                    continue

                defaults = map_card(card_data)
                defaults["set_id"] = set_id

                _, created = Card.objects.update_or_create(
                    id=card_data["id"],
                    defaults=defaults,
                )
                if created:
                    stats["cards_created"] += 1
                else:
                    stats["cards_updated"] += 1

        return stats
