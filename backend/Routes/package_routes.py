from flask import Blueprint, request, jsonify
import requests
import os
import urllib.parse

bp = Blueprint('packages', __name__)

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


@bp.route('/package', methods=['POST'])
def holiday_package():
    data = request.json
    origin = data.get('origin')
    destination = data.get('destination')
    departure_date = data.get('departure_date')
    return_date = data.get('return_date')
    adults = data.get('adults', 1)

    if not origin or not destination or not departure_date or not return_date:
        return jsonify({'error': 'Missing required fields'}), 400

    try:
        token = get_amadeus_token()
        if not token:
            return jsonify({'error': 'Failed to authenticate with Amadeus API'}), 500

        headers = {'Authorization': f'Bearer {token}'}

        # Flight search
        flight_url = f'{AMADEUS_BASE_URL}/v2/shopping/flight-offers'
        flight_params = {
            'originLocationCode': origin,
            'destinationLocationCode': destination,
            'departureDate': departure_date,
            'returnDate': return_date,
            'adults': adults,
            'max': 3
        }
        flight_resp = requests.get(flight_url, headers=headers, params=flight_params)
        flight_resp.raise_for_status()
        flights = flight_resp.json().get('data', [])

        # Hotel search
        hotel_url = f'{AMADEUS_BASE_URL}/v2/shopping/hotel-offers'
        hotel_params = {
            'cityCode': destination,
            'checkInDate': departure_date,
            'checkOutDate': return_date,
            'adults': adults
        }
        hotel_resp = requests.get(hotel_url, headers=headers, params=hotel_params)
        hotel_resp.raise_for_status()
        hotels = hotel_resp.json().get('data', [])

        return jsonify({
            'destination': destination,
            'flights': flights,
            'hotels': hotels
        })

    except requests.HTTPError as e:
        return jsonify({'error': str(e), 'details': e.response.json()}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
