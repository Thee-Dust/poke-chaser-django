---
name: poke-chaser-django
description: Conventions, patterns, and dev commands for the poke-chaser-django REST API (Django + DRF). Use when adding endpoints, models, serializers, migrations, or pagination to this project.
disable-model-invocation: true
---

# Poke Chaser Django

Django REST Framework API for a Pokémon TCG card tracker. Data is synced from the [Pokemon TCG API](https://docs.pokemontcg.io) and served read-only to the frontend.

## API endpoints

```
GET /cards/cardSet/                    list sets         ?sort=  paginated 18/page
GET /cards/cardSet/{id}/               single set
GET /cards/cardSet/{id}/cards/         cards in a set    ?search= ?sort=  paginated 24/page
GET /cards/card/                       all cards         ?search= ?sort=  paginated 24/page
GET /cards/card/{id}/                  single card
```

Router is in `pokechaser/cards/urls.py`. Root mount is `path("cards/", include("pokechaser.cards.urls"))` in `pokechaser/urls.py`.

## Pagination

All list responses use a custom shape — never the default DRF format. Inherit `PaginatedResponse` from `views.py` for any new paginated endpoint.

```json
{
  "links": { "first": "...", "last": "...", "next": "...", "prev": null },
  "meta": { "pagination": { "page": 1, "pages": 10, "count": 173 } },
  "results": [...]
}
```

Per-endpoint page sizes (never use global `PAGE_SIZE`):
- `CardSetPagination` — 18
- `CardPagination` — 24
- New endpoint: add a class inheriting `PaginatedResponse` with `page_size = N`.

## Sort and search

`sort_cards()` and `search_cards()` are module-level helpers in `views.py`. Reuse them — do not duplicate.

**Card number ordering** — `number` is a `CharField`. Use `(Length("number"), "number")` for correct numeric order (`"1"`, `"2"`, `"10"` not `"1"`, `"10"`, `"2"`).

**Price sorting** annotates via:
```python
Coalesce(
    F("tcgplayer__prices__normal__market"),
    F("tcgplayer__prices__holofoil__market"),
    F("tcgplayer__prices__reverseHolofoil__market"),
    Value(None),
    output_field=FloatField(),
)
```

**Search** matches against `name`, `set__name`, `rarity`, `supertype` with `icontains`.

**Set sort values**: `release_date_desc` (default), `release_date_asc`, `name_asc`, `name_desc`

**Card sort values**: `number_asc` (default), `number_desc`, `name_asc`, `name_desc`, `price_desc`, `price_asc`

## Models

`BaseModel` (abstract, `pokechaser/core/models.py`) adds `created_at` / `updated_at` to every model.

`CardSet.id` and `Card.id` are **string PKs** (e.g. `"sv8"`, `"sv8-1"`). When registering a viewset:
```python
router.register(r"card", views.CardViewSet, basename="card")  # basename required
# viewset: lookup_field = "id"
```

JSON fields (`attacks`, `weaknesses`, `abilities`, `tcgplayer`, `cardmarket`, etc.) store raw API JSON. Inner keys stay **camelCase** as returned by the Pokemon TCG API.

New `Card` fields must have `default=` or `null=True, blank=True` so existing rows are not broken.

## Serializers

- Derived FK fields use `source=`: `set_name = serializers.CharField(source="set.name", read_only=True)`
- Always pair `select_related("set")` with any queryset that reads `set.name`
- Exclude sync metadata from serializer fields: `created_at`, `updated_at`, `updated_at_api`

## Adding a new endpoint checklist

1. Add model fields if needed → run migrations
2. Add/update serializer fields
3. Add viewset (inherit `ReadOnlyModelViewSet`), set `pagination_class`, `serializer_class`, `lookup_field`
4. Register in `pokechaser/cards/urls.py`
5. For nested actions use `@action(detail=True, pagination_class=...)`

## Dev commands

```bash
# Migrations
docker compose exec app python manage.py makemigrations cards
docker compose exec app python manage.py migrate

# Sync data from Pokemon TCG API (backfills new fields)
docker compose exec app python manage.py sync_pokemon_cards

# Shell
docker compose exec app python manage.py shell
```

Sync also runs automatically via Celery every 14 days (`pokechaser/cards/tasks.py`).

## CORS

`django-cors-headers` is installed. Allowed origins are set via `CORS_ALLOWED_ORIGINS` env var (comma-separated). For local dev, `CORS_ALLOW_ALL_ORIGINS = DEBUG` is an acceptable shortcut.

## Settings conventions

- `rest_framework` and `corsheaders` are in `INSTALLED_APPS`
- `CorsMiddleware` must be before `CommonMiddleware` in `MIDDLEWARE`
- `REST_FRAMEWORK` block has no global `PAGE_SIZE` — pagination is per-viewset only
