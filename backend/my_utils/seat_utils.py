def extract_available_seats(seatmap_response):
    """
    Extracts available seats from the Amadeus seat map response and
    formats them for frontend usage.
    
    Returns:
        List of dictionaries with segmentId and available seats.
    """
    formatted = []

    try:
        for seatmap in seatmap_response.get("data", []):
            segment_id = seatmap.get("segmentId")

            # Most responses have only 1 deck
            decks = seatmap.get("decks", [])
            if not decks:
                continue

            deck = decks[0]
            seats = deck.get("seats", [])

            available_seats = []
            for seat in seats:
                if seat.get("seatAvailabilityStatus") == "AVAILABLE":
                    traveler_pricing = seat.get("travelerPricing", [{}])[0]

                    seat_info = {
                        "number": seat.get("number"),
                        "travelerId": traveler_pricing.get("travelerId"),
                        "price": traveler_pricing.get("total", "0"),
                        "currency": traveler_pricing.get("price", {}).get("currency", "INR"),
                        "characteristics": seat.get("characteristics", []),
                        "coordinates": seat.get("coordinates", {}),
                        "isChargeable": traveler_pricing.get("total", "0") != "0"
                    }
                    available_seats.append(seat_info)

            formatted.append({
                "segmentId": segment_id,
                "availableSeats": available_seats
            })

        return formatted

    except Exception as e:
        print(f"[Seat Extraction Error]: {e}")
        return []
