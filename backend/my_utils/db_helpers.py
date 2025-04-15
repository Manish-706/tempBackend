import logging
from database import get_connection

# Helper function to save flight order to DB
def save_flight_order_to_db(order_data):
    

    connection = get_connection()
    rows_inserted = 0
    try:
        order_id = order_data.get('order_id')  # Ensure order_id is available
        if not order_id:
            raise ValueError("Missing order_id in the order data")

        logging.info(f"Saving flight order for order_id: {order_id}")

        with connection.cursor() as cursor:
            flight_offer = order_data.get('flightOffers', [{}])[0]
            pnr = order_data.get('associatedRecords', [{}])[0].get('reference', '')
            offer_id = flight_offer.get('id')
            price = flight_offer.get('price', {}).get('grandTotal', 0)
            currency = flight_offer.get('price', {}).get('currency', 'USD')
            itineraries = flight_offer.get('itineraries', [])

            for traveler in order_data.get('travelers', []):
                name_info = traveler.get('name', {})
                contact_info = traveler.get('contact', {})

                first_name = name_info.get('firstName', '')
                last_name = name_info.get('lastName', '')
                email = contact_info.get('emailAddress', '')

                if not email:
                    logging.warning(f"Missing email for traveler: {first_name} {last_name}")

                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        try:
                            dep_airport = segment['departure'].get('iataCode', '')
                            arr_airport = segment['arrival'].get('iataCode', '')
                            dep_time = segment['departure'].get('at', '')
                            arr_time = segment['arrival'].get('at', '')

                            if not dep_airport or not arr_airport or not dep_time or not arr_time:
                                logging.warning(f"Incomplete segment data for {first_name} {last_name}, skipping insert.")
                                continue

                            sql = """
                            INSERT INTO flight_orders (
                                flight_order_id, order_id, pnr, flight_offer_id,
                                departure_airport, arrival_airport,
                                departure_time, arrival_time,
                                traveler_first_name, traveler_last_name,
                                traveler_email, total_price, currency, status
                            ) VALUES (
                                %(flight_order_id)s, %(order_id)s, %(pnr)s, %(offer_id)s,
                                %(dep_airport)s, %(arr_airport)s,
                                %(dep_time)s, %(arr_time)s,
                                %(first_name)s, %(last_name)s,
                                %(email)s, %(price)s, %(currency)s, %(status)s
                            )
                            """
                            params = {
                                'flight_order_id': order_data.get('id'),
                                'order_id': order_id,
                                'pnr': pnr,
                                'offer_id': offer_id,
                                'dep_airport': dep_airport,
                                'arr_airport': arr_airport,
                                'dep_time': dep_time,
                                'arr_time': arr_time,
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': email,
                                'price': price,
                                'currency': currency,
                                'status': 'pending'
                            }

                            logging.debug(f"SQL Query: {sql}")
                            logging.debug(f"Parameters: {params}")

                            cursor.execute(sql, params)
                            rows_inserted += 1

                        except Exception as e:
                            logging.error(f"Error inserting segment for traveler {first_name} {last_name}: {e}")
                            continue

            connection.commit()
            logging.info(f"Successfully inserted {rows_inserted} flight order(s) into the database.")
            return rows_inserted

    except Exception as e:
        logging.error(f"Error saving flight order to DB: {e}")
        connection.rollback()
        raise
    finally:
        connection.close()