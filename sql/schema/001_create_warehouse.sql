-- Create schemas for the flight reliability platform
CREATE SCHEMA IF NOT EXISTS staging;
CREATE SCHEMA IF NOT EXISTS warehouse;


-- Date dimension
CREATE TABLE IF NOT EXISTS warehouse.dim_date (
    date_key INTEGER PRIMARY KEY,
    full_date DATE NOT NULL UNIQUE,
    year_number SMALLINT NOT NULL,
    quarter_number SMALLINT NOT NULL
        CHECK (quarter_number BETWEEN 1 AND 4),
    month_number SMALLINT NOT NULL
        CHECK (month_number BETWEEN 1 AND 12),
    month_name VARCHAR(20) NOT NULL,
    day_of_month SMALLINT NOT NULL
        CHECK (day_of_month BETWEEN 1 AND 31),
    day_of_week_number SMALLINT NOT NULL
        CHECK (day_of_week_number BETWEEN 1 AND 7),
    day_name VARCHAR(20) NOT NULL,
    is_weekend BOOLEAN NOT NULL
);


-- Airline dimension
CREATE TABLE IF NOT EXISTS warehouse.dim_airline (
    airline_key INTEGER
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    reporting_airline_id INTEGER NOT NULL UNIQUE,
    reporting_airline_code VARCHAR(10) NOT NULL
);


-- Airport dimension
CREATE TABLE IF NOT EXISTS warehouse.dim_airport (
    airport_key INTEGER
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    airport_id INTEGER NOT NULL UNIQUE,
    airport_code VARCHAR(10) NOT NULL,
    city_name VARCHAR(100),
    state_code VARCHAR(10),
    state_name VARCHAR(100)
);


-- Main flight fact table
CREATE TABLE IF NOT EXISTS warehouse.fact_flight (
    flight_key BIGINT
        GENERATED ALWAYS AS IDENTITY
        PRIMARY KEY,

    date_key INTEGER NOT NULL,
    airline_key INTEGER NOT NULL,
    origin_airport_key INTEGER NOT NULL,
    destination_airport_key INTEGER NOT NULL,

    flight_number INTEGER NOT NULL,
    tail_number VARCHAR(20),
    route_code VARCHAR(25) NOT NULL,

    scheduled_departure_time SMALLINT NOT NULL,
    actual_departure_time SMALLINT,
    scheduled_departure_hour SMALLINT
        CHECK (
            scheduled_departure_hour IS NULL
            OR scheduled_departure_hour BETWEEN 0 AND 23
        ),
    departure_time_block VARCHAR(20),

    scheduled_arrival_time SMALLINT NOT NULL,
    actual_arrival_time SMALLINT,
    scheduled_arrival_hour SMALLINT
        CHECK (
            scheduled_arrival_hour IS NULL
            OR scheduled_arrival_hour BETWEEN 0 AND 23
        ),
    arrival_time_block VARCHAR(20),

    departure_delay_minutes_signed REAL,
    departure_delay_minutes REAL,
    departure_delayed_15 BOOLEAN,

    arrival_delay_minutes_signed REAL,
    arrival_delay_minutes REAL,
    arrival_delayed_15 BOOLEAN,
    arrival_on_time BOOLEAN,

    taxi_out_minutes REAL,
    taxi_in_minutes REAL,
    scheduled_elapsed_minutes REAL,
    actual_elapsed_minutes REAL,
    air_time_minutes REAL,

    flight_count SMALLINT NOT NULL DEFAULT 1,
    distance_miles REAL NOT NULL,
    distance_group SMALLINT,

    cancelled BOOLEAN NOT NULL,
    cancellation_code VARCHAR(5),
    diverted BOOLEAN NOT NULL,
    flight_status VARCHAR(20) NOT NULL
        CHECK (
            flight_status IN (
                'Completed',
                'Cancelled',
                'Diverted'
            )
        ),

    delay_cause_reported BOOLEAN NOT NULL,
    carrier_delay_minutes REAL NOT NULL DEFAULT 0,
    weather_delay_minutes REAL NOT NULL DEFAULT 0,
    national_air_system_delay_minutes REAL NOT NULL DEFAULT 0,
    security_delay_minutes REAL NOT NULL DEFAULT 0,
    late_aircraft_delay_minutes REAL NOT NULL DEFAULT 0,
    total_reported_delay_minutes REAL NOT NULL DEFAULT 0,

    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fact_flight_date_foreign_key
        FOREIGN KEY (date_key)
        REFERENCES warehouse.dim_date (date_key),

    CONSTRAINT fact_flight_airline_foreign_key
        FOREIGN KEY (airline_key)
        REFERENCES warehouse.dim_airline (airline_key),

    CONSTRAINT fact_flight_origin_airport_foreign_key
        FOREIGN KEY (origin_airport_key)
        REFERENCES warehouse.dim_airport (airport_key),

    CONSTRAINT fact_flight_destination_airport_foreign_key
        FOREIGN KEY (destination_airport_key)
        REFERENCES warehouse.dim_airport (airport_key),

    CONSTRAINT fact_flight_unique_scheduled_segment
        UNIQUE (
            date_key,
            airline_key,
            flight_number,
            origin_airport_key,
            destination_airport_key,
            scheduled_departure_time
        ),

    CONSTRAINT fact_flight_non_negative_values
        CHECK (
            departure_delay_minutes IS NULL
            OR departure_delay_minutes >= 0
        ),

    CONSTRAINT fact_flight_non_negative_arrival_delay
        CHECK (
            arrival_delay_minutes IS NULL
            OR arrival_delay_minutes >= 0
        ),

    CONSTRAINT fact_flight_non_negative_distance
        CHECK (distance_miles >= 0),

    CONSTRAINT fact_flight_status_indicators
        CHECK (
            (
                flight_status = 'Completed'
                AND cancelled = FALSE
                AND diverted = FALSE
            )
            OR
            (
                flight_status = 'Cancelled'
                AND cancelled = TRUE
                AND diverted = FALSE
            )
            OR
            (
                flight_status = 'Diverted'
                AND cancelled = FALSE
                AND diverted = TRUE
            )
        )
);


-- Indexes used by common dashboard filters and SQL queries
CREATE INDEX IF NOT EXISTS fact_flight_date_key_index
    ON warehouse.fact_flight (date_key);

CREATE INDEX IF NOT EXISTS fact_flight_airline_key_index
    ON warehouse.fact_flight (airline_key);

CREATE INDEX IF NOT EXISTS fact_flight_origin_airport_index
    ON warehouse.fact_flight (origin_airport_key);

CREATE INDEX IF NOT EXISTS fact_flight_destination_airport_index
    ON warehouse.fact_flight (destination_airport_key);

CREATE INDEX IF NOT EXISTS fact_flight_route_index
    ON warehouse.fact_flight (
        origin_airport_key,
        destination_airport_key
    );

CREATE INDEX IF NOT EXISTS fact_flight_status_index
    ON warehouse.fact_flight (flight_status);