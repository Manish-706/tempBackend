CREATE DATABASE Travels;
USE Travels;

-- USERS TABLE
CREATE TABLE users (
    user_id INT AUTO_INCREMENT PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    email VARCHAR(100) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    passport_number VARCHAR(50) UNIQUE,  -- Ensure unique passport numbers across users
    date_of_birth DATE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    user_type ENUM('customer', 'admin', 'agent') NOT NULL,
    INDEX idx_email (email),
    INDEX idx_phone (phone)
) ENGINE=InnoDB;

-- USER CREDENTIALS TABLE
CREATE TABLE user_credentials (
    user_id INT PRIMARY KEY,
    password_hash VARCHAR(255) NOT NULL,
    last_login DATETIME,
    failed_attempts INT DEFAULT 0,
    is_locked BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
) ENGINE=InnoDB;

-- LOCATIONS TABLE
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

-- AIRLINES TABLE
CREATE TABLE airlines (
    airline_id INT AUTO_INCREMENT PRIMARY KEY,
    iata_code CHAR(2) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    country_code CHAR(2) NOT NULL,
    fleet_size SMALLINT,
    INDEX idx_airline_name (name)
) ENGINE=InnoDB;

-- FLIGHTS TABLE
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
    INDEX idx_departure_time (departure_time),
    CONSTRAINT chk_flight_times CHECK (departure_time < arrival_time)
) ENGINE=InnoDB;

-- ORDERS TABLE
CREATE TABLE orders (
    order_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    flight_offer_id INT NOT NULL,
    status ENUM('pending', 'confirmed', 'cancelled') DEFAULT 'pending',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (flight_offer_id) REFERENCES flight_offers(flight_offer_id)
) ENGINE=InnoDB;


-- HOTEL ORDERS TABLE
CREATE TABLE hotel_orders (
    hotel_order_id INT AUTO_INCREMENT PRIMARY KEY,
    order_id INT NOT NULL,
    hotel_name VARCHAR(100),
    location VARCHAR(100),
    check_in_date DATE,
    check_out_date DATE,
    total_price DECIMAL(10, 2),
    FOREIGN KEY (order_id) REFERENCES orders(order_id)
) ENGINE=InnoDB;

-- CAB SERVICES TABLE
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

-- TOUR PACKAGES TABLE
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

-- VISA APPLICATIONS TABLE
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

-- BOOKINGS TABLE
CREATE TABLE bookings (
    booking_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    service_type ENUM('flight', 'hotel', 'cab', 'package') NOT NULL,
    service_id INT NOT NULL,
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    total_amount DECIMAL(12,2) NOT NULL,
    currency CHAR(3) DEFAULT 'USD',
    status ENUM('pending', 'confirmed', 'canceled') DEFAULT 'pending',
    payment_status ENUM('unpaid', 'paid', 'refunded') DEFAULT 'unpaid',
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    INDEX idx_booking_date (booking_date),
    INDEX idx_service (service_type, service_id)
) ENGINE=InnoDB;

-- PAYMENTS TABLE
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

-- PENDING REGISTRATIONS TABLE
CREATE TABLE pending_registrations (
    email VARCHAR(100) PRIMARY KEY,
    first_name VARCHAR(50) NOT NULL,
    last_name VARCHAR(50) NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    phone VARCHAR(20),
    passport_number VARCHAR(50),  -- Passport number is optional until verified for international purposes
    date_of_birth DATE,
    user_type ENUM('customer', 'admin', 'agent') NOT NULL,
    otp VARCHAR(6) NOT NULL,
    otp_expiry_time DATETIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_pending_email (email)
) ENGINE=InnoDB;

CREATE TABLE flight_orders (
    id INT AUTO_INCREMENT PRIMARY KEY,
    flight_order_id VARCHAR(100) NOT NULL,
    pnr VARCHAR(20) NOT NULL,
    flight_offer_id VARCHAR(50),
    departure_airport VARCHAR(10),
    arrival_airport VARCHAR(10),
    departure_time DATETIME,
    arrival_time DATETIME,
    traveler_first_name VARCHAR(100),
    traveler_last_name VARCHAR(100),
    traveler_email VARCHAR(100),
    total_price DECIMAL(10, 2),
    currency VARCHAR(10),
    booking_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status ENUM('pending', 'confirmed', 'canceled') DEFAULT 'pending',
    INDEX idx_pnr (pnr)
) ENGINE=InnoDB;

-- ITINERARIES TABLE
CREATE TABLE itineraries (
    id INT AUTO_INCREMENT PRIMARY KEY,
    booking_id INT,
    duration VARCHAR(20),
    FOREIGN KEY (booking_id) REFERENCES bookings(booking_id)
);

-- SEGMENTS TABLE
CREATE TABLE segments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    itinerary_id INT,
    segment_order INT,
    departure_airport VARCHAR(5),
    arrival_airport VARCHAR(5),
    departure_time DATETIME,
    arrival_time DATETIME,
    flight_number VARCHAR(10),
    carrier_code VARCHAR(5),
    aircraft_code VARCHAR(10),
    duration VARCHAR(20),
    stops INT,
    cabin_class VARCHAR(10),
    baggage_allowance VARCHAR(10),
    FOREIGN KEY (itinerary_id) REFERENCES itineraries(id)
);

CREATE TABLE airport_countries (
    iata_code VARCHAR(10) PRIMARY KEY,
    country_code VARCHAR(5)
);
CREATE TABLE travelers (
    traveler_id INT PRIMARY KEY AUTO_INCREMENT,
    user_id INT,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    email VARCHAR(255),
    phone VARCHAR(20),
    order_id VARCHAR(255),  -- This matches the data type of flight_orders(flight_order_id)
    -- other fields specific to the traveler
    FOREIGN KEY (user_id) REFERENCES users(user_id),
    FOREIGN KEY (order_id) REFERENCES flight_orders(flight_order_id)
);




ALTER TABLE flight_orders
ADD COLUMN order_id INT PRIMARY KEY AUTO_INCREMENT;


select * from airport_countries
where country_code = 'IN';

ALTER TABLE orders MODIFY order_id INT AUTO_INCREMENT;

ALTER TABLE flight_orders DROP FOREIGN KEY flight_orders_ibfk_1;
ALTER TABLE flight_orders DROP COLUMN order_id;

ALTER TABLE flight_orders DROP PRIMARY KEY;

ALTER TABLE flight_orders 
    DROP PRIMARY KEY,
    ADD COLUMN id INT AUTO_INCREMENT PRIMARY KEY FIRST;

DESCRIBE flight_orders;

DESCRIBE orders;

select * from pending_registrations;
select * from users;
select * from travelers;

select * from flight_orders;
SELECT *FROM orders WHERE order_id = 'order_QHI2mITfIsfFNT';
select * from segments;


