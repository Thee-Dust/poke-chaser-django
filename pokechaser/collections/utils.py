from pokechaser.cards.price_types import ALL_PRICE_TYPES


def get_tcgplayer_market_price(card):
    """
    Return the TCGPlayer market price for a card as a float, or None.
    Returns the maximum market price found across all known TCGPlayer price
    types so old-set cards (1stEditionHolofoil, unlimitedHolofoil, etc.)
    are priced correctly, consistent with the sort logic in cards/views.py.
    """
    tcgplayer = card.tcgplayer
    if not tcgplayer or "prices" not in tcgplayer:
        return None
    prices = tcgplayer["prices"]
    candidates = [
        price_data["market"]
        for pt in ALL_PRICE_TYPES
        if (price_data := prices.get(pt)) and price_data.get("market") is not None
    ]
    return max(candidates) if candidates else None
