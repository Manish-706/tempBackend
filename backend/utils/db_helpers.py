# Save flight order to the database
def save_flight_order_to_db(order_data, user_id):
    connection = get_connection()
    rows_inserted = 0
    try:
        order_id = order_data.get('id')
        if not order_id:
            raise ValueError("Missing order_id in the order data")

        logging.info(f"Saving flight order for order_id: {order_id}")

        with connection.cursor() as cursor:
            flight_offer = order_data.get('flightOffer', {})
            pnr = order_data.get('associatedRecords', [{}])[0].get('reference', '')
            flight_offer_id = flight_offer.get('id')
            price = flight_offer.get('price', {}).get('grandTotal', 0)
            currency = flight_offer.get('price', {}).get('currency', 'USD')
            itineraries = flight_offer.get('itineraries', [])

            for traveler in order_data.get('passengers', []):
                first_name = traveler.get('firstName', '')
                last_name = traveler.get('lastName', '')
                email = traveler.get('email', '')

                for itinerary in itineraries:
                    for segment in itinerary.get('segments', []):
                        try:
                            # Prepare the SQL statement
                            sql = """
                            INSERT INTO flight_orders (
                                user_id, flight_order_id, pnr, flight_offer_id,
                                departure_airport, arrival_airport,
                                departure_time, arrival_time,
                                traveler_first_name, traveler_last_name,
                                traveler_email, total_price, currency
                            ) VALUES (
                                %(user_id)s, %(flight_order_id)s, %(pnr)s, %(flight_offer_id)s,
                                %(dep_airport)s, %(arr_airport)s,
                                %(dep_time)s, %(arr_time)s,
                                %(first_name)s, %(last_name)s,
                                %(email)s, %(price)s, %(currency)s
                            )
                            """
                            # Parameters for SQL
                            params = {
                                'user_id': user_id,
                                'flight_order_id': order_id,
                                'pnr': pnr,
                                'flight_offer_id': flight_offer_id,
                                'dep_airport': segment['departure'].get('iataCode', ''),
                                'arr_airport': segment['arrival'].get('iataCode', ''),
                                'dep_time': segment['departure'].get('at', ''),
                                'arr_time': segment['arrival'].get('at', ''),
                                'first_name': first_name,
                                'last_name': last_name,
                                'email': email,
                                'price': price,
                                'currency': currency
                            }

                            # Log the SQL for debugging purposes
                            logging.debug(f"SQL Query: {sql}")
                            logging.debug(f"Parameters: {params}")

                            # Execute the SQL
                            cursor.execute(sql, params)
                            rows_inserted += 1

                            if rows_inserted % 100 == 0:
                                connection.commit()  # Commit every 100 rows

                        except Exception as e:
                            logging.error(f"Error inserting segment for traveler {first_name} {last_name}: {e}")
                            raise

            connection.commit()  # Commit remaining rows
            logging.info(f"Successfully inserted {rows_inserted} flight order(s) into the database.")
            return rows_inserted

    except Exception as e:
        logging.error(f"Error saving flight order to DB: {e}")
        connection.rollback()  # Rollback on error
        raise
    finally:
        connection.close()
