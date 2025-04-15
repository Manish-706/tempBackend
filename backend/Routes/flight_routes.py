from flask import Blueprint, request, jsonify
import requests
import re
import urllib.parse
import os
import json
from database import get_connection
from datetime import datetime, timedelta
from flask_cors import cross_origin
from my_utils.db_helpers import save_flight_order_to_db
from my_utils.pdf_generator import generate_ticket_pdf
from my_utils.seat_utils import extract_available_seats
import logging


# Set up loggingpip
logging.basicConfig(level=logging.INFO)


bp = Blueprint("flights", __name__)

AMADEUS_CLIENT_ID = os.environ.get('AMADEUS_CLIENT_ID', "LU7IEumxc5eFAYlRJKRZ88RfSuCvP6ql")
AMADEUS_CLIENT_SECRET = os.environ.get('AMADEUS_CLIENT_SECRET', "G3JqkJS4Q5gboLUQ")
AMADEUS_BASE_URL = "https://test.api.amadeus.com"

cached_token = None
token_expiry = datetime.utcnow()

def get_amadeus_token():
    global cached_token, token_expiry

    # Return cached token if still valid
    if cached_token and datetime.utcnow() < token_expiry:
        print("[TOKEN] Using cached token.")
        return cached_token

    print("[TOKEN] Fetching new token...")
    auth_url = f"{AMADEUS_BASE_URL}/v1/security/oauth2/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "grant_type": "client_credentials",
        "client_id": AMADEUS_CLIENT_ID,
        "client_secret": AMADEUS_CLIENT_SECRET
    }

    try:
        response = requests.post(auth_url, headers=headers, data=urllib.parse.urlencode(data))
        response.raise_for_status()

        token_data = response.json()
        print("[TOKEN] Token response:", token_data)

        cached_token = token_data.get("access_token")
        expires_in = token_data.get("expires_in", 1800)
        token_expiry = datetime.utcnow() + timedelta(seconds=expires_in)

        return cached_token

    except requests.exceptions.RequestException as e:
        print(f"[TOKEN] Error fetching token: {e}")
        if e.response is not None:
            print("[TOKEN] Response content:", e.response.text)
        return None


def is_valid_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        return date_obj >= datetime.now().date()  # Check if date is today or in the future
    except ValueError:
        return False

@bp.before_app_request
def handle_options():
    if request.method == "OPTIONS":
        return '', 200, {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type, Authorization"
        } 

# IATA_COUNTRY_MAP = {
#     "DEL": "IN", "BOM": "IN", "BLR": "IN", "HYD": "IN", "MAA": "IN", "CCU": "IN"
# }

def get_country_by_airport(iata_code):
    # First, check DB
    result = db_query_airport_country(iata_code)
    if result:
        return result
    
    # Fallback: Amadeus API
    try:
        response = requests.get(
            f"{AMADEUS_BASE_URL}/v1/reference-data/locations",
            params={"keyword": iata_code, "subType": "AIRPORT"},
            headers={"Authorization": f"Bearer {get_amadeus_token()}"}
        )
        data = response.json()
        if data and data.get("data"):
            country = data["data"][0]["address"]["countryCode"]
            # optionally cache to DB
            return country
    except:
        return None

    return None


def is_international_flight(flight_offer):
    # Extract the airport IATA codes for the first and last segments
    from_iata = flight_offer['itineraries'][0]['segments'][0]['departure']['iataCode']
    to_iata = flight_offer['itineraries'][0]['segments'][-1]['arrival']['iataCode']

    # Get country codes for the departure and arrival airports
    from_country = get_country_for_airport(from_iata)
    to_country = get_country_for_airport(to_iata)

    if from_country == "UNKNOWN" or to_country == "UNKNOWN":
        print(f"Warning: Missing country info for {from_iata} or {to_iata}")
        return False  # Safe fallback: treat as domestic

    return from_country != to_country



def build_travelers_list(passengers, flight_offer):
    # Determine if the flight is international
    is_international = is_international_flight(flight_offer)
    travelers = []

    for idx, p in enumerate(passengers, start=1):
        name = p.get("name", {})
        contact = p.get("contact", {})
        phones = contact.get("phones", [])
        
        # Ensure that each phone number exists or create a default
        if not phones:
            phones = [{
                "deviceType": "MOBILE",
                "countryCallingCode": contact.get("countryCode", "91"),
                "number": contact.get("phoneNumber", "")
            }]
        
        traveler = {
            "id": str(idx),  # Traveler ID
            "dateOfBirth": p.get("dateOfBirth", ""),  # Date of birth
            "gender": p.get("gender", ""),  # Gender
            "name": {
                "firstName": name.get("firstName", ""),  # First name
                "lastName": name.get("lastName", "")  # Last name
            },
            "contact": {
                "emailAddress": contact.get("emailAddress", ""),  # Email
                "phones": phones  # Phones
            }
        }

        # If the flight is international, add passport details
        if is_international:
            traveler["documents"] = [{
                "documentType": "PASSPORT",  # Passport type
                "number": p.get("passportNumber", "P0000000"),  # Default value if not provided
                "expiryDate": p.get("passportExpiry", "2030-01-01"),  # Default expiry date
                "issuanceCountry": p.get("passportIssuanceCountry", "IN"),  # Default issuance country
                "nationality": p.get("nationality", "IN"),  # Default nationality
                "holder": True  # Holder set to True for primary traveler
            }]
        
        travelers.append(traveler)

    return travelers

airline_cache = {}

def get_airline_name(code, token):
    if code in airline_cache:
        return airline_cache[code]

    url = f"{AMADEUS_BASE_URL}/v1/reference-data/airlines"
    headers = {"Authorization": f"Bearer {token}"}
    params = {"airlineCodes": code}

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("data"):
            name = data["data"][0].get("businessName") or data["data"][0].get("commonName") or code
            airline_cache[code] = name
            return name
        else:
            return code
    except Exception as e:
        print(f"Failed to fetch airline name for {code}: {e}")
        return code

def parse_duration(iso_duration):
    match = re.match(r'PT(?:(\d+)H)?(?:(\d+)M)?', iso_duration)
    if not match:
        return iso_duration
    hours = match.group(1) or '0'
    minutes = match.group(2) or '0'
    return f"{int(hours)}h {int(minutes)}m"


def format_datetime(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str)
        return dt.strftime('%Y-%m-%d %H:%M')
    except Exception:
        return iso_str

def get_city_name(iata_code, token):
    # You can use Amadeus API or your DB here
    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"
    params = {"subType": "AIRPORT", "keyword": iata_code}
    headers = {"Authorization": f"Bearer {token}"}
    try:
        res = requests.get(url, headers=headers, params=params)
        res.raise_for_status()
        data = res.json()
        return data["data"][0]["address"]["cityName"]
    except:
        return iata_code

@bp.route('/real-time', methods=['GET', 'OPTIONS'])
@cross_origin(origins="*")
def get_real_time_flights():
    departure = request.args.get("from")
    arrival = request.args.get("to")
    departure_date = request.args.get("date")
    trip_type = request.args.get("tripType", "oneway").lower()
    return_date = request.args.get("returnDate")
    adults = request.args.get("adults", 1)
    max_offers = request.args.get("max", 20)

    try:
        adults = int(adults)
        max_offers = int(max_offers)
    except ValueError:
        return jsonify({"error": "adults and max must be integers"}), 400

    token = get_amadeus_token()
    if not token:
        return jsonify({"error": "Authentication failed"}), 401

    headers = {"Authorization": f"Bearer {token}"}

    if trip_type == "multicity":
        segments = request.args.get("segments")
        if not segments:
            return jsonify({"error": "For multicity, provide 'segments' parameter as JSON array"}), 400
        try:
            segments = json.loads(segments)
        except Exception as e:
            return jsonify({"error": "Invalid 'segments' JSON format", "details": str(e)}), 400

        results = []
        try:
            for index, segment in enumerate(segments):
                origin = segment.get("from")
                destination = segment.get("to")
                date = segment.get("date")

                if not origin or not destination or not is_valid_date(date):
                    return jsonify({"error": f"Invalid segment: {segment}"}), 400

                flight_params = {
                    "originLocationCode": origin,
                    "destinationLocationCode": destination,
                    "departureDate": date,
                    "adults": adults,
                    "currencyCode": "INR",
                    "nonStop": "false",
                    "max": max_offers
                }

                url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
                response = requests.get(url, headers=headers, params=flight_params)
                response.raise_for_status()
                segment_data = response.json()

                offers = []
                for offer in segment_data.get("data", []):
                    codes = offer.get("validatingAirlineCodes", [])
                    full_names = [get_airline_name(code, token) for code in codes]

                    formatted_itineraries = []
                    for itin in offer.get("itineraries", []):
                        segments = []
                        for seg in itin.get("segments", []):
                            departure_code = seg["departure"]["iataCode"]
                            arrival_code = seg["arrival"]["iataCode"]
                            segments.append({
                                "departure": {
                                    "city": get_city_name(departure_code, token),
                                    "airport": departure_code,
                                    "time": format_datetime(seg["departure"]["at"]),
                                    "terminal": seg["departure"].get("terminal", "N/A")  # Added terminal info
                                },
                                "arrival": {
                                    "city": get_city_name(arrival_code, token),
                                    "airport": arrival_code,
                                    "time": format_datetime(seg["arrival"]["at"]),
                                    "terminal": seg["arrival"].get("terminal", "N/A")  # Added terminal info
                                },
                                "duration": parse_duration(seg["duration"]),
                                "airline": seg["carrierCode"],
                                "flightNumber": seg["number"]
                            })
                        formatted_itineraries.append({
                            "duration": parse_duration(itin.get("duration", "")),
                            "segments": segments
                        })

                    offers.append({
                        "id": offer.get("id"),
                        "instantTicketingRequired": offer.get("instantTicketingRequired", False),
                        "isUpsellOffer": offer.get("isUpsellOffer", False),
                        "itineraries": formatted_itineraries,
                        "lastTicketingDate": offer.get("lastTicketingDate"),
                        "lastTicketingDateTime": offer.get("lastTicketingDateTime"),
                        "nonHomogeneous": offer.get("nonHomogeneous", False),
                        "numberOfBookableSeats": offer.get("numberOfBookableSeats"),
                        "oneWay": offer.get("oneWay", False),
                        "price": offer.get("price"),
                        "pricingOptions": offer.get("pricingOptions"),
                        "source": offer.get("source"),
                        "travelerPricings": offer.get("travelerPricings"),
                        "type": offer.get("type"),
                        "validatingAirlineCodes": codes,
                        "validatingAirlines": full_names
                    })

                results.append({
                    "segmentIndex": index + 1,
                    "route": f"{origin} → {destination}",
                    "date": date,
                    "offers": offers
                })

            return jsonify({
                "tripType": "multicity",
                "segments": results
            }), 200

        except requests.exceptions.RequestException as e:
            return jsonify({"error": "API request failed for one or more segments", "details": str(e)}), 500

    else:
        if not departure or not arrival or not departure_date:
            return jsonify({"error": "Please provide 'from', 'to', and 'date'"}), 400

        if not is_valid_date(departure_date):
            return jsonify({"error": "Invalid departure date format, use YYYY-MM-DD"}), 400

        params = {
            "originLocationCode": departure,
            "destinationLocationCode": arrival,
            "departureDate": departure_date,
            "adults": adults,
            "currencyCode": "INR",
            "nonStop": "false",
            "max": max_offers
        }

        if trip_type == "roundtrip":
            if not return_date:
                return jsonify({"error": "Return date is required for roundtrip"}), 400
            if not is_valid_date(return_date):
                return jsonify({"error": "Invalid return date format, use YYYY-MM-DD"}), 400
            params["returnDate"] = return_date

        try:
            url = f"{AMADEUS_BASE_URL}/v2/shopping/flight-offers"
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            data = response.json()

            if "errors" in data:
                return jsonify({"error": data["errors"]}), 400

            offers = []
            for offer in data.get("data", []):
                codes = offer.get("validatingAirlineCodes", [])
                full_names = [get_airline_name(code, token) for code in codes]

                formatted_itineraries = []
                for itin in offer.get("itineraries", []):
                    segments = []
                    for seg in itin.get("segments", []):
                        departure_code = seg["departure"]["iataCode"]
                        arrival_code = seg["arrival"]["iataCode"]
                        segments.append({
                            "departure": {
                                "city": get_city_name(departure_code, token),
                                "airport": departure_code,
                                "time": format_datetime(seg["departure"]["at"]),
                                "terminal": seg["departure"].get("terminal", "N/A")  # Added terminal info
                            },
                            "arrival": {
                                "city": get_city_name(arrival_code, token),
                                "airport": arrival_code,
                                "time": format_datetime(seg["arrival"]["at"]),
                                "terminal": seg["arrival"].get("terminal", "N/A")  # Added terminal info
                            },
                            "duration": parse_duration(seg["duration"]),
                            "airline": seg["carrierCode"],
                            "flightNumber": seg["number"]
                        })
                    formatted_itineraries.append({
                        "duration": parse_duration(itin.get("duration", "")),
                        "segments": segments
                    })

                offers.append({
                    "id": offer.get("id"),
                    "instantTicketingRequired": offer.get("instantTicketingRequired", False),
                    "isUpsellOffer": offer.get("isUpsellOffer", False),
                    "itineraries": formatted_itineraries,
                    "lastTicketingDate": offer.get("lastTicketingDate"),
                    "lastTicketingDateTime": offer.get("lastTicketingDateTime"),
                    "nonHomogeneous": offer.get("nonHomogeneous", False),
                    "numberOfBookableSeats": offer.get("numberOfBookableSeats"),
                    "oneWay": offer.get("oneWay", False),
                    "price": offer.get("price"),
                    "pricingOptions": offer.get("pricingOptions"),
                    "source": offer.get("source"),
                    "travelerPricings": offer.get("travelerPricings"),
                    "type": offer.get("type"),
                    "validatingAirlineCodes": codes,
                    "validatingAirlines": full_names
                })

            return jsonify({
                "tripType": trip_type,
                "flightOffers": offers
            }), 200

        except requests.exceptions.RequestException as e:
            return jsonify({"error": f"API Request Failed: {str(e)}"}), 500

@bp.route('/flight-price', methods=['POST'])
@cross_origin(origins="*")
def price_flight_offer():
    token = get_amadeus_token()
    if not token:
        return jsonify({"error": "Authentication failed"}), 401

    try:
        data = request.get_json()
        if not data or 'flightOffers' not in data:
            return jsonify({"error": "Missing flightOffers in request body"}), 400

        payload = {
            "data": {
                "type": "flight-offers-pricing",
                "flightOffers": data['flightOffers']
            }           
        }

        url = f"{AMADEUS_BASE_URL}/v1/shopping/flight-offers/pricing"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        print(f"Error pricing flight offer: {e}")
        return jsonify({"error": str(e)}), 500
    
@bp.route('/start-booking', methods=['POST'])
@cross_origin(origins="*")
def start_booking():
    body = request.get_json()
    flight_offer = body.get("flightOffer")
    travelers = body.get("travelers")

    if not flight_offer or not travelers:
        return jsonify({"error": "Missing flightOffer or travelers"}), 400

    # International passport check
    if is_international_flight(flight_offer):
        for traveler in travelers:
            if not all(traveler.get(k) for k in ["passportNumber", "passportExpiry", "passportCountry"]):
                return jsonify({"error": "Passport details required for international flights"}), 400

    try:
        # Base flight fare
        base_amount = float(flight_offer["price"]["grandTotal"]) * 100  # in paise

        # Add seat charges (optional)
        seat_total = 0
        for t in travelers:
            if "seat" in t and "price" in t["seat"]:
                try:
                    seat_total += float(t["seat"]["price"]) * 100
                except:
                    continue  # skip if malformed

        total_amount = int(base_amount + seat_total)
        currency = flight_offer["price"]["currency"]

        return jsonify({
            "message": "Ready for payment. Proceed with Razorpay.",
            "amount": total_amount,
            "currency": currency,
            "flightOffer": flight_offer,
            "travelers": travelers
        }), 200

    except Exception as e:
        return jsonify({"error": "Error calculating final amount", "details": str(e)}), 500

    
@bp.route('/seat-map', methods=['POST'])
@cross_origin(origins="*")
def get_seat_map():
    token = get_amadeus_token()
    if not token:
        return jsonify({"error": "Authentication failed"}), 401

    body = request.get_json()

    if not body or 'flightOffer' not in body:
        return jsonify({"error": "Missing 'flightOffer' in body"}), 400

    flight_offer = body['flightOffer']

    try:
        url = f"{AMADEUS_BASE_URL}/v1/shopping/seatmaps"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }
        payload = {
            "data": [flight_offer]
        }

        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()

        seatmap_data = response.json()
        available_seats = extract_available_seats(seatmap_data)

        return jsonify({
            "availableSeats": available_seats,
            "raw": seatmap_data  # Optional: helpful for debugging or development
        }), 200

    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500

@bp.route('/search-location', methods=['GET'])
@cross_origin(origins="*")
def search_location_by_keyword():
    keyword = request.args.get('keyword')
    
    if not keyword:
        return jsonify({"error": "Missing keyword"}), 400

    # Check if the keyword looks like an IATA code (e.g., 3 uppercase letters)
    if len(keyword) == 3 and keyword.isupper():
        # It's an IATA code, so fetch the location directly
        return get_location_by_id(keyword)

    # Otherwise, treat the keyword as a location name and search by keyword
    token = get_amadeus_token()
    if not token:
        return jsonify({"error": "Authentication failed"}), 401

    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations"
    headers = {"Authorization": f"Bearer {token}"}
    params = {
        "subType": "CITY,AIRPORT",
        "keyword": keyword,
        "page[limit]": 10
    }

    try:
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        return jsonify({"error": str(e)}), 500



@bp.route('/get-location/<location_id>', methods=['GET'])
@cross_origin(origins="*")
def get_location_by_id(location_id):
    token = get_amadeus_token()
    if not token:
        return jsonify({"error": "Authentication failed"}), 401

    url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/{location_id}"
    headers = {"Authorization": f"Bearer {token}"}

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        return jsonify(response.json()), 200
    except requests.exceptions.RequestException as e:
        print(f"Error: {str(e)} Response: {response.text}")  # Log response text
        return jsonify({"error": str(e)}), 500




def get_country_for_airport(iata_code):
    # Try fetching from DB first
    try:
        conn = get_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT country_code FROM airport_countries WHERE iata_code = %s", (iata_code,))
            result = cur.fetchone()
            if result:
                return result['country_code']
    except Exception as e:
        print(f"[DB Error fetching country]: {e}")

    # If not found in DB, fetch from Amadeus and insert
    return fetch_and_save_airport_country(iata_code)

def fetch_and_save_airport_country(iata_code):
    """Fetches the country from Amadeus and stores it in DB if not found in DB."""
    try:
        token = get_amadeus_token()
        url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/{iata_code}"
        headers = {"Authorization": f"Bearer {token}"}
        response = requests.get(url, headers=headers)
        data = response.json()

        country_code = data["data"]["address"]["countryCode"]

        # Save to DB
        try:
            conn = get_connection()
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO airport_countries (iata_code, country_code) VALUES (%s, %s)",
                    (iata_code, country_code)
                )
                conn.commit()
        except Exception as db_insert_err:
            print(f"[DB Insert Error]: {db_insert_err}")

        return country_code
    except Exception as e:
        print(f"[Amadeus Error]: {e}")
        return "UNKNOWN"

def update_airports_in_db(iata_codes):
    for iata_code in iata_codes:
        country_code = fetch_and_save_airport_country(iata_code)
        if country_code != "UNKNOWN":
            print(f"Successfully saved {iata_code} with country {country_code}")
        else:
            print(f"Failed to fetch or save data for {iata_code}")

# Route to create a flight order
@bp.route('/create-order', methods=['POST'])
@cross_origin(origins="*")
def create_flight_order():
    token = get_amadeus_token()

    if not token:
        logging.error("Authentication failed: Token not available")
        return jsonify({"error": "Authentication failed"}), 401

    try:
        request_data = request.get_json()
        logging.debug(f"Request data: {request_data}")

        data = request_data.get("data", {})

        if not data or 'flightOffers' not in data or 'travelers' not in data:
            logging.error("Missing 'flightOffers' or 'travelers' in request body")
            return jsonify({"error": "Missing 'flightOffers' or 'travelers' in request body"}), 400

        if len(data['flightOffers']) == 0 or len(data['travelers']) == 0:
            logging.error("Flight offers or travelers are empty")
            return jsonify({"error": "Flight offers or travelers are empty"}), 400

        flight_offer = data['flightOffers'][0]
        travelers_data = data['travelers']

        for traveler in travelers_data:
            name = traveler.get("name", {})
            contact = traveler.get("contact", {})
            if not name.get("firstName") or not name.get("lastName"):
                return jsonify({"error": "Missing traveler name details"}), 400
            if not contact.get("emailAddress") or not contact.get("phones"):
                return jsonify({"error": "Missing traveler contact details"}), 400

        travelers = build_travelers_list(travelers_data, flight_offer)
        clean_offer = clean_flight_offer(flight_offer)

        data_payload = {
            "type": "flight-order",
            "flightOffers": [clean_offer],
            "travelers": travelers
        }

        logging.info(f"Sending request to Amadeus API: {data_payload}")

        url = f"{AMADEUS_BASE_URL}/v1/booking/flight-orders"
        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json"
        }

        response = requests.post(url, headers=headers, json={"data": data_payload})
        response.raise_for_status()

        order_response = response.json()
        flight_order = order_response.get("data")

        if not flight_order:
            logging.error("Missing 'data' in Amadeus response")
            return jsonify({"error": "Missing 'data' in Amadeus response"}), 500

        # Ensure that order_id is set, either from the API response or generated manually
        if not flight_order.get('id'):
            logging.error("Missing 'order_id' in the Amadeus flight order response.")
            return jsonify({"error": "Missing 'order_id' in the Amadeus response"}), 500

        # Set order_id to flight_order's id if missing
        flight_order['order_id'] = flight_order.get('id')  # Ensure that order_id is available

        # Save flight order to database (without user_id)
        try:
            rows_inserted = save_flight_order_to_db(flight_order)
            if rows_inserted == 0:
                logging.error(f"Failed to insert flight order into DB for order_id: {flight_order.get('id')}")
                return jsonify({"error": "Failed to save flight order to database"}), 500
        except Exception as db_error:
            logging.error(f"Failed to save flight order to database: {str(db_error)}")
            return jsonify({
                "error": "Order created, but failed to save to database",
                "db_error": str(db_error),
                "order_data": flight_order
            }), 500

        # Generate the ticket PDF
        pdf_path = generate_ticket_pdf(flight_order)
        logging.info(f"Flight order created and PDF generated at {pdf_path}")

        return jsonify({
            "message": "Flight order created successfully",
            "order_data": flight_order,
            "pdf_path": pdf_path
        }), 200

    except requests.exceptions.HTTPError as e:
        try:
            error_response = e.response.json() if e.response else str(e)
            logging.error(f"Amadeus API Error: {error_response}")
            return jsonify({
                "error": "Amadeus API request failed",
                "details": error_response
            }), e.response.status_code if e.response else 500
        except Exception as inner_e:
            logging.error(f"Error parsing Amadeus API response: {inner_e}")
            return jsonify({
                "error": "Error parsing Amadeus API error response",
                "details": str(inner_e)
            }), 500

    except Exception as e:
        logging.error(f"Server error: {str(e)}")
        return jsonify({
            "error": "Server error",
            "details": str(e)
        }), 500


# Helper function to clean the flight offer
def clean_flight_offer(flight_offer):
    import copy
    offer = copy.deepcopy(flight_offer)

    for itinerary in offer.get("itineraries", []):
        for segment in itinerary.get("segments", []):
            segment.pop("airlineName", None)
            segment.get("departure", {}).pop("city", None)
            segment.get("arrival", {}).pop("city", None)

    offer.pop("validatingAirlines", None)

    for traveler_pricing in offer.get("travelerPricings", []):
        for fare_details in traveler_pricing.get("fareDetailsBySegment", []):
            fare_details.pop("includedCabinBags", None)
            fare_details.pop("amenities", None)

    return offer


