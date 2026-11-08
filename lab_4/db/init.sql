CREATE TABLE IF NOT EXISTS flights (
    id              BIGSERIAL PRIMARY KEY,
    carrier         VARCHAR(3) NOT NULL,
    flight_number   VARCHAR(8) NOT NULL,
    origin          CHAR(3)    NOT NULL,
    destination     CHAR(3)    NOT NULL,
    departure_time  TIMESTAMP  NOT NULL,
    arrival_time    TIMESTAMP  NOT NULL,
    price           INTEGER    NOT NULL CHECK (price > 0),
    CONSTRAINT flights_uniq UNIQUE (flight_number, departure_time)
);

-- выборка рейсов за дату: departure_time >= :d AND departure_time < :d + 1 день
CREATE INDEX IF NOT EXISTS idx_flights_departure ON flights (departure_time);
