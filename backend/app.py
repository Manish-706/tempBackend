from flask import Flask
import os
from flask_caching import Cache
from Routes import user_routes, flight_routes, booking_routes, package_routes, hotels_routes, payment_routes

app = Flask(__name__)
app.config.from_pyfile('config.py')
port = int(os.environ.get("PORT", 10000))
# Configure caching
cache = Cache(app, config={'CACHE_TYPE': 'simple'})

# Register blueprints
app.register_blueprint(user_routes.bp, url_prefix='/users')
app.register_blueprint(flight_routes.bp, url_prefix='/flights')
app.register_blueprint(booking_routes.bp, url_prefix='/bookings')
app.register_blueprint(hotels_routes.bp, url_prefix='/hotels')
app.register_blueprint(package_routes.bp, url_prefix='/packages')
app.register_blueprint(payment_routes.bp, url_prefix='/payments')  # 👈 new line

app.get('/')
def index():
    print("Welcome to the Flight Booking API!")
    return "Welcome to the Flight Booking API!"

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=port)
