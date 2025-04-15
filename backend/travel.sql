CREATE DATABASE Travels;
USE Travels;




CREATE TABLE locations (
    location_id INT AUTO_INCREMENT PRIMARY KEY,
    country_code CHAR(2) NOT NULL,
    city VARCHAR(50) NOT NULL,
    airport_code CHAR(3),
    latitude DECIMAL(9,6),
    longitude DECIMAL(9,6),
    timezone VARCHAR(50),
    UNIQUE KEY unique_location (country_code, city),
    INDEX idx_airport (airport_code)
) ENGINE=InnoDB;



CREATE TABLE airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    iata_code CHAR(2) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    fleet_size SMALLINT,
    INDEX idx_airline_name (name)
) ENGINE=InnoDB;


CREATE TABLE flights (
    flight_id INT AUTO_INCREMENT PRIMARY KEY,
    airline_id INT NOT NULL,
    flight_number VARCHAR(6) NOT NULL,
    departure_location INT NOT NULL,
    arrival_location INT NOT NULL,
    departure_time DATETIME NOT NULL,
    arrival_time DATETIME NOT NULL,
    aircraft_type VARCHAR(50),
    class ENUM('economy', 'premium', 'business', 'first') NOT NULL,
    base_price DECIMAL(10,2) NOT NULL,
    status ENUM('scheduled', 'delayed', 'canceled', 'departed'),
    FOREIGN KEY (airline_id) REFERENCES airlines(airline_id),
    FOREIGN KEY (departure_location) REFERENCES locations(location_id),
    FOREIGN KEY (arrival_location) REFERENCES locations(location_id),
    INDEX idx_flight_number (flight_number),
    INDEX idx_departure_time (departure_time)
) ENGINE=InnoDB;


CREATE TABLE hotels (
    hotel_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    location_id INT NOT NULL,
    star_rating TINYINT CHECK (star_rating BETWEEN 1 AND 5),
    amenities SET('pool', 'gym', 'spa', 'wifi', 'restaurant'),
    check_in_time TIME,
    check_out_time TIME,
    FOREIGN KEY (location_id) REFERENCES locations(location_id),
    FULLTEXT INDEX idx_hotel_name (name)
) ENGINE=InnoDB;


CREATE TABLE cab_services (
    cab_id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_type ENUM('hatchback', 'sedan', 'suv', 'luxury') NOT NULL,
    capacity TINYINT NOT NULL,
    current_location INT NOT NULL,
    available BOOLEAN DEFAULT TRUE,
    driver_id INT NOT NULL,
    FOREIGN KEY (current_location) REFERENCES locations(location_id),
    INDEX idx_availability (available)
) ENGINE=InnoDB;

CREATE TABLE tour_packages (
    package_id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    duration_days SMALLINT NOT NULL,
    price DECIMAL(12,2) NOT NULL,
    included_services JSON NOT NULL,
    departure_date DATE NOT NULL,
    available_seats SMALLINT NOT NULL,
    status ENUM('active', 'expired', 'sold-out') DEFAULT 'active',
    INDEX idx_departure_date (departure_date)
) ENGINE=InnoDB;


CREATE TABLE visa_applications (
    application_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    country_code CHAR(2) NOT NULL,
    visa_type ENUM('tourist', 'business', 'student') NOT NULL,
    application_date DATE NOT NULL,
    status ENUM('pending', 'approved', 'rejected') DEFAULT 'pending',
    documents JSON,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_visa_status (status)
) ENGINE=InnoDB;

CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    service_type ENUM('flight', 'hotel', 'cab', 'package') NOT NULL,
    service_id INT NOT NULL,  -- References respective service tables
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'confirmed', 'canceled') DEFAULT 'pending',
    payment_status ENUM('unpaid', 'paid', 'refunded') DEFAULT 'unpaid',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_booking_date (booking_date),
    INDEX idx_service (service_type, service_id)
) ENGINE=InnoDB;

CREATE TABLE payments (
    payment_id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT NOT NULL,
    amount DECIMAL(12,2) NOT NULL,
    payment_method ENUM('credit_card', 'paypal', 'bank_transfer') NOT NULL,
    transaction_id VARCHAR(255) NOT NULL,
    payment_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('success', 'failed', 'pending') NOT NULL,
    gateway_response TEXT,
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id),
    INDEX idx_transaction (transaction_id),
    INDEX idx_payment_status (status)
) ENGINE=InnoDB;


CREATE TABLE pending_registrations (
    email VARCHAR(100) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    passport_number VARCHAR(50),
    date_of_birth DATE,
    user_type ENUM('customer', 'admin', 'agent') NOT NULL,
    otp VARCHAR(6) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pending_email (email)
) ENGINE=InnoDB;



DESCRIBE flights;

select * from users;
