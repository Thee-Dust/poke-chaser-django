def get_tcgplayer_market_price(card):
    """
    Return the TCGPlayer market price for a card as a float, or None.
    Priority: normal → holofoil → reverseHolofoil, matching the price sort logic in cards/views.py.
    """
    tcgplayer = card.tcgplayer
    if not tcgplayer or "prices" not in tcgplayer:
        return None
    prices = tcgplayer["prices"]
    for price_type in ("normal", "holofoil", "reverseHolofoil"):
        price_data = prices.get(price_type)
        if price_data and price_data.get("market") is not None:
            return price_data["market"]
    return None
