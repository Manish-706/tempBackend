from flask import Blueprint, request, jsonify, render_template_string
import razorpay
from flask_cors import cross_origin
import os
bp = Blueprint("payments", __name__)

RAZORPAY_KEY_ID = os.environ.get("RAZORPAY_KEY_ID", "rzp_test_cwytGMG7H8rA6c")
RAZORPAY_KEY_SECRET = os.environ.get("RAZORPAY_KEY_SECRET", "xx3CTyvKyALUsfHaSVKo4Oox")
razorpay_client = razorpay.Client(auth=(RAZORPAY_KEY_ID, RAZORPAY_KEY_SECRET))

from datetime import datetime

@bp.route('/create-payment-order', methods=['POST'])
@cross_origin(origins="*")
def create_payment_order():
    data = request.get_json()
    amount = data.get("amount")
    currency = data.get("currency", "INR")
    flight_offer = data.get("flightOffer")  # Optional: for generating receipt

    if not amount:
        return jsonify({"error": "Amount is required"}), 400

    # Generate dynamic receipt ID
    try:
        if flight_offer:
            departure_code = flight_offer["itineraries"][0]["segments"][0]["departure"]["iataCode"]
            arrival_code = flight_offer["itineraries"][0]["segments"][0]["arrival"]["iataCode"]
            departure_date = flight_offer["itineraries"][0]["segments"][0]["departure"]["at"].split("T")[0]
            receipt = f"receipt_{departure_code}_{arrival_code}_{departure_date}"
        else:
            receipt = f"receipt_generic_{int(datetime.now().timestamp())}"
    except Exception as e:
        print("Receipt generation failed:", str(e))
        receipt = f"receipt_fallback_{int(datetime.now().timestamp())}"

    # Create Razorpay order
    try:
        order = razorpay_client.order.create({
            "amount": int(amount),
            "currency": currency,
            "receipt": receipt,
            "payment_capture": 1
        })
        return jsonify({
            "order_id": order['id'],
            "amount": order['amount'],
            "currency": order['currency'],
            "receipt": order['receipt']
        }), 200
    except Exception as e:
        return jsonify({"error": str(e), "receipt": receipt}), 500

    

@bp.route('/verify-payment', methods=['POST'])
@cross_origin(origins="*")
def verify_payment():
    data = request.get_json()
    try:
        params_dict = {
            'razorpay_order_id': data['razorpay_order_id'],
            'razorpay_payment_id': data['razorpay_payment_id'],
            'razorpay_signature': data['razorpay_signature']
        }

        razorpay_client.utility.verify_payment_signature(params_dict)
        return jsonify({"status": "Payment Verified"}), 200
    except razorpay.errors.SignatureVerificationError:
        return jsonify({"error": "Payment verification failed"}), 400
    

@bp.route('/test-payment-page')
def test_payment_page():
    return render_template_string("""
    <!DOCTYPE html>
    <html>
    <head>
      <title>Razorpay Test</title>
      <script src="https://checkout.razorpay.com/v1/checkout.js"></script>
    </head>
    <body>
      <h2>Test Razorpay Payment</h2>
      <button id="pay-btn">Pay ₹11,934</button>

      <script>
        document.getElementById('pay-btn').onclick = function () {
          const options = {
            "key": "rzp_test_cwytGMG7H8rA6c", // Your Razorpay test key
            "amount": 1193400, // in paise
            "currency": "INR",
            "name": "Flight Booking",
            "description": "Test Transaction",
            "order_id": "order_QH0TGTZ9mvwe79", // Replace with your generated order_id
            "handler": function (response) {
              alert("Payment ID: " + response.razorpay_payment_id);
              alert("Order ID: " + response.razorpay_order_id);
              alert("Signature: " + response.razorpay_signature);

              // Optionally send to your backend
              fetch("/payment/verify-payment", {
                method: "POST",
                headers: {
                  "Content-Type": "application/json"
                },
                body: JSON.stringify(response)
              }).then(res => res.json())
                .then(data => alert("Server response: " + JSON.stringify(data)))
                .catch(err => console.error(err));
            },
            "prefill": {
              "name": "Harshit",
              "email": "test@example.com",
              "contact": "9999999999"
            },
            "theme": {
              "color": "#3399cc"
            }
          };
          const rzp1 = new Razorpay(options);
          rzp1.open();
        };
      </script>
    </body>
    </html>
    """)