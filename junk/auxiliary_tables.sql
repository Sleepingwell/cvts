Create table if not exists vehicle_days(
    vehicle_id INTEGER,         -- Or TEXT, whatever type we are using as unique identifier for a vehicle
    observation_date date,      -- Date for which we are sumarising for, considering one entry per active vehicle.day
    num_pings INTEGER,          -- Count of pings in a minute
    distance REAL,              -- Total distance covered by the vehicle as the haversine distance between each sequence of pings  
    regularity_5_minutes REAL,  -- number of 5 minutes intervals for which there is a ping divided by the number of 5 minutes intervals of activity
    regularity_15_minutes REAL, -- Same as above, but for 15 minutes intervals
    regularity_1_hour REAL,     -- Same as above, but for 1h interval
    coverage GEOMETRY);         -- Bounding box of the vehicles' pings -> We could use 4 columns for min/max xy as well

Create table if not exists vehicles(
    vehicle_id INTEGER,  -- Or TEXT, whatever type we are using as unique identifier for a vehicle
    first_activity date, -- Date of the first activity registered
    last_activity date,  -- Date of the last activity registered
    active_days INTEGER, -- Number of days with activity
    num_pings INTEGER,   -- Total number of pings in the database
    distance REAL,       -- total distance covered
    active_time INTEGER, -- total time active (in seconds, or minutes or any other measure we would like)
    coverage GEOMETRY);  -- Bounding box of the vehicles' pings -> We could use 4 columns for min/max xy as well

Create table if not exists stops(
    vehicle_id INTEGER,       -- Or TEXT, whatever type we are using as unique identifier for a vehicle
    stop_index_date smallint, -- Index of the stop for that vehicle that day. So the departure point would be 0, the first stop 1, the second stop 2.... The last ping of the day would be n-1
    stop_date date,           -- Date for this stop
    stop_start timestamp,     -- Time of the stop start
    stop_end timestamp,       -- Time of the stop end
    stop_duration INTEGER,    -- Stop duration (in seconds/minutes or timedelta)
    position GEOMETRY);       -- Position of the stop
