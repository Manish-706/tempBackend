from flask import Blueprint, request, jsonify
from database import get_connection
from werkzeug.security import generate_password_hash
import random
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta, timezone
import traceback
import logging
bp = Blueprint('users', __name__)

def generate_otp(length=6):
    return ''.join(str(random.randint(0, 9)) for _ in range(length))

def send_otp_sms(phone_number, otp):
    try:
        print(f"[DEV] OTP for {phone_number}: {otp}")  # ✅ Terminal log only
        # Integrate actual SMS service here
        return True
    except Exception:
        return False

def send_otp_email(recipient_email, otp):
    try:
        smtp_server = "smtp.example.com"
        smtp_port = 587
        smtp_username = "your_email@example.com"
        smtp_password = "your_email_password"

        subject = "Your OTP for Registration"
        body = f"Your OTP for registration is: {otp}. It will expire in 10 minutes."
        msg = MIMEText(body)
        msg["Subject"] = subject
        msg["From"] = smtp_username
        msg["To"] = recipient_email

        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.sendmail(smtp_username, [recipient_email], msg.as_string())
        server.quit()

        print(f"[DEV] OTP for {recipient_email}: {otp}")  # ✅ Terminal log only
        return True
    except Exception:
        return False

@bp.route('/register', methods=['POST'])
def register_user():
    data = request.get_json()

    required_fields = ['first_name', 'last_name', 'email', 'password', 'phone']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'error': f'{field.replace("_", " ").title()} is required'}), 400

    email = data['email'].lower()
    phone = data['phone']
    first_name = data['first_name']
    last_name = data['last_name']
    password = data['password']
    passport_number = data.get('passport_number')
    date_of_birth = data.get('date_of_birth')
    user_type = data.get('user_type', 'customer')
    otp_channel = data.get('otp_channel', 'mobile')

    if user_type not in ['customer', 'admin', 'agent']:
        return jsonify({'error': 'Invalid user type'}), 400

    password_hash = generate_password_hash(password)
    otp = generate_otp()
    otp_expiry_time = datetime.now(timezone.utc) + timedelta(minutes=10)

    connection = get_connection()
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT email FROM users WHERE email = %s", (email,))
            if cursor.fetchone():
                return jsonify({'error': 'Email already registered'}), 400

            cursor.execute("SELECT phone FROM users WHERE phone = %s", (phone,))
            if cursor.fetchone():
                return jsonify({'error': 'Phone number already registered'}), 400

            cursor.execute("DELETE FROM pending_registrations WHERE email = %s OR phone = %s", (email, phone))

            sql = """
                INSERT INTO pending_registrations 
                (first_name, last_name, email, password_hash, phone, passport_number, date_of_birth, user_type, otp, otp_expiry_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(sql, (
                first_name, last_name, email, password_hash, phone,
                passport_number, date_of_birth, user_type, otp, otp_expiry_time
            ))
            connection.commit()

        otp_sent = send_otp_email(email, otp) if otp_channel == 'email' else send_otp_sms(phone, otp)

        if otp_sent:
            return jsonify({
                'message': f'OTP sent to your {otp_channel}',
                'email': email
            }), 200
        else:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM pending_registrations WHERE email = %s OR phone = %s", (email, phone))
                connection.commit()
            return jsonify({'error': f'Failed to send OTP via {otp_channel}. Please try again.'}), 500

    except Exception:
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        connection.close()

@bp.route('/verify-otp', methods=['POST'])
def verify_otp():
    connection = get_connection()
    try:
        data = request.json
        email = data.get('email')
        otp = data.get('otp')

        if not email or not otp:
            return jsonify({'error': 'Email and OTP are required'}), 400

        with connection.cursor() as cursor:
            cursor.execute("SELECT * FROM pending_registrations WHERE email = %s", (email,))
            row = cursor.fetchone()
            if not row:
                return jsonify({'error': 'User not found or OTP expired'}), 404

            pending_user = row
            db_otp = str(pending_user['otp']).zfill(6)
            submitted_otp = str(otp).zfill(6)

            if db_otp != submitted_otp:
                return jsonify({'error': 'Invalid OTP'}), 400

            expiry_time = pending_user.get('otp_expiry_time')
            current_time = datetime.now(timezone.utc)

            if expiry_time is None:
                return jsonify({'error': 'OTP expiry not set'}), 500

            if isinstance(expiry_time, str):
                try:
                    expiry_time = datetime.fromisoformat(expiry_time)
                except ValueError:
                    expiry_time = datetime.strptime(expiry_time, '%Y-%m-%d %H:%M:%S')

            if current_time > expiry_time.replace(tzinfo=timezone.utc):
                return jsonify({'error': 'OTP expired'}), 400

            # Check if passport_number already exists in users table
            passport_number = pending_user.get('passport_number')
            if passport_number:
                cursor.execute("SELECT passport_number FROM users WHERE passport_number = %s", (passport_number,))
                if cursor.fetchone():
                    return jsonify({'error': 'Passport number already registered'}), 400

            # Insert the user data into the users table
            insert_query = """
                INSERT INTO users (first_name, last_name, email, password_hash, phone, passport_number, date_of_birth, user_type)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (
                pending_user['first_name'],
                pending_user['last_name'],
                pending_user['email'],
                pending_user['password_hash'],
                pending_user['phone'],
                pending_user['passport_number'],
                pending_user['date_of_birth'],
                pending_user['user_type']
            ))

            # Get the user_id of the newly created user
            user_id = cursor.lastrowid  # Assuming auto-incremented user_id

            # Insert the traveler data into the travelers table
            insert_travelers_query = """
                INSERT INTO travelers (user_id, first_name, last_name, email, phone, order_id)
                VALUES (%s, %s, %s, %s, %s, %s)
            """
            cursor.execute(insert_travelers_query, (
                user_id,
                pending_user['first_name'],
                pending_user['last_name'],
                pending_user['email'],
                pending_user['phone'],
                None  # order_id can be set later when there's a booking
            ))

            # Remove the pending registration from the pending_registrations table
            cursor.execute("DELETE FROM pending_registrations WHERE email = %s", (email,))
            connection.commit()

        return jsonify({'message': 'OTP verified. Registration successful.'}), 200

    except Exception as e:
        logging.error(f"Error in OTP verification: {str(e)}")
        logging.error(traceback.format_exc())
        return jsonify({'error': 'Internal server error'}), 500
    finally:
        connection.close()
