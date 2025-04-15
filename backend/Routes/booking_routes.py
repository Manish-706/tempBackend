# routes/booking_routes.py

from flask import Blueprint, request, jsonify
from database import get_connection

bp = Blueprint('bookings', __name__)

# POST /bookings - Create a new booking
@bp.route('/', methods=['POST'])
def create_booking():
    data = request.get_json()
    user_id = data.get('user_id')
    flight_id = data.get('flight_id')
    status = data.get('status', 'Booked')  # Default status
    payment_status = data.get('payment_status', 'Pending')  # Default payment status

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = """
                INSERT INTO bookings (user_id, flight_id, status, payment_status)
                VALUES (%s, %s, %s, %s)
            """
            cursor.execute(sql, (user_id, flight_id, status, payment_status))
            connection.commit()
            booking_id = cursor.lastrowid
        return jsonify({'message': 'Booking created successfully', 'booking_id': booking_id}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        connection.close()

# GET /bookings - Retrieve all bookings or filter by user_id
@bp.route('/', methods=['GET'])
def get_bookings():
    user_id = request.args.get('user_id')
    query = "SELECT * FROM bookings"
    params = []

    if user_id:
        query += " WHERE user_id = %s"
        params.append(user_id)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute(query, tuple(params))
            bookings = cursor.fetchall()
        return jsonify(bookings), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        connection.close()

# GET /bookings/<int:booking_id> - Retrieve details for a specific booking
@bp.route('/<int:booking_id>', methods=['GET'])
def get_booking(booking_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = "SELECT * FROM bookings WHERE id = %s"
            cursor.execute(sql, (booking_id,))
            booking = cursor.fetchone()
        if booking:
            return jsonify(booking), 200
        else:
            return jsonify({'error': 'Booking not found'}), 404
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        connection.close()

# PUT /bookings/<int:booking_id> - Update a booking (status or payment_status)
@bp.route('/<int:booking_id>', methods=['PUT'])
def update_booking(booking_id):
    data = request.get_json()
    status = data.get('status')
    payment_status = data.get('payment_status')

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = "UPDATE bookings SET status = %s, payment_status = %s WHERE id = %s"
            cursor.execute(sql, (status, payment_status, booking_id))
            connection.commit()
        return jsonify({'message': 'Booking updated successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        connection.close()

# DELETE /bookings/<int:booking_id> - Delete (or cancel) a booking
@bp.route('/<int:booking_id>', methods=['DELETE'])
def delete_booking(booking_id):
    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            sql = "DELETE FROM bookings WHERE id = %s"
            cursor.execute(sql, (booking_id,))
            connection.commit()
        return jsonify({'message': 'Booking deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 400
    finally:
        connection.close()
