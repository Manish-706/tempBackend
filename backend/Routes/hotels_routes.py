import os
import urllib.parse
import requests
from flask import Blueprint, request, jsonify

# Create a blueprint for hotel search
bp = Blueprint('Hotels', __name__)

# Amadeus API credentials
AMADEUS_CLIENT_ID = os.environ.get('AMADEUS_CLIENT_ID', "LU7IEumxc5eFAYlRJKRZ88RfSuCvP6ql")
AMADEUS_CLIENT_SECRET = os.environ.get('AMADEUS_CLIENT_SECRET', "G3JqkJS4Q5gboLUQ")
AMADEUS_BASE_URL = "https://test.api.amadeus.com"

def get_amadeus_token():
    """Obtain Amadeus API access token."""
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
        token = response.json().get("access_token")
        print("✅ Access Token:", token)
        return token
    except requests.exceptions.RequestException as e:
        print(f"❌ Error getting Amadeus token: {e}")
        return None

def get_hotel_ids(destination, access_token):
    """Fetch hotel IDs for a given city."""
    hotel_list_url = f"{AMADEUS_BASE_URL}/v1/reference-data/locations/hotels/by-city"
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {"cityCode": destination}

    response = requests.get(hotel_list_url, headers=headers, params=params)
    
    if response.status_code == 200:
        hotels = response.json().get("data", [])
        hotel_ids = [hotel["hotelId"] for hotel in hotels]
        print(f"✅ Found {len(hotel_ids)} hotels in {destination}: {hotel_ids}")
        return hotel_ids
    else:
        print("❌ Error fetching hotel IDs:", response.text)
        return None

def fetch_hotel_offers(hotel_ids, access_token, check_in_date, check_out_date, adults):
    """Fetch hotel offers in batches of 10 hotels at a time."""
    hotel_offers_url = f"{AMADEUS_BASE_URL}/v3/shopping/hotel-offers"
    headers = {"Authorization": f"Bearer {access_token}"}
    
    if not hotel_ids:
        print("❌ No hotel IDs found.")
        return []

    hotel_offers = []
    batch_size = 10  # Amadeus allows a limited number per request
    
    for i in range(0, len(hotel_ids), batch_size):
        batch = hotel_ids[i:i + batch_size]
        params = {
            "hotelIds": ",".join(batch),
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "adults": adults
        }

        response = requests.get(hotel_offers_url, headers=headers, params=params)
        
        if response.status_code == 200:
            offers = response.json().get("data", [])
            print(f"✅ Batch {i//batch_size + 1}: Retrieved {len(offers)} offers.")
            hotel_offers.extend(offers)
        else:
            print(f"❌ Error fetching hotel offers for batch {i//batch_size + 1}: {response.text}")

    print(f"✅ Total offers fetched: {len(hotel_offers)}")
    return hotel_offers

@bp.route('/search', methods=['GET'])
def search_holiday_packages():
    """Search hotels based on user query parameters."""
    destination = request.args.get("destination")
    check_in_date = request.args.get("check_in_date")
    check_out_date = request.args.get("check_out_date")
    adults = int(request.args.get("adults", 1))  # Ensure it's an integer

    if not destination or not check_in_date or not check_out_date:
        return jsonify({"error": "Missing required parameters"}), 400

    access_token = get_amadeus_token()
    if not access_token:
        return jsonify({"error": "Failed to authenticate with Amadeus API"}), 500

    hotel_ids = get_hotel_ids(destination, access_token)
    if not hotel_ids or len(hotel_ids) == 0:
        return jsonify({"error": "No hotels found for the given destination"}), 404

    hotel_offers = fetch_hotel_offers(hotel_ids, access_token, check_in_date, check_out_date, adults)
    
    return jsonify({"hotels": hotel_offers})
