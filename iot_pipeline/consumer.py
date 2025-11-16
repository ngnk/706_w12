import json
import psycopg2
from kafka import KafkaConsumer
from datetime import datetime

def run_consumer():
    """Consumes IoT sensor messages from Kafka and inserts them into PostgreSQL."""
    try:
        print("[Consumer] Connecting to Kafka at localhost:9092...")
        consumer = KafkaConsumer(
            "iot_sensors",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="earliest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="iot-consumer-group",
        )
        print("[Consumer] ✓ Connected to Kafka successfully!")
        
        print("[Consumer] Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            dbname="iot_db",
            user="iot_user",
            password="iot_password",
            host="localhost",
            port="5432",
        )
        conn.autocommit = True
        cur = conn.cursor()
        print("[Consumer] ✓ Connected to PostgreSQL successfully!")

        # Create table for raw sensor readings
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS sensor_readings (
                id SERIAL PRIMARY KEY,
                sensor_id VARCHAR(100),
                sensor_type VARCHAR(50),
                location VARCHAR(100),
                value NUMERIC(10, 2),
                timestamp TIMESTAMP,
                anomaly BOOLEAN,
                unit VARCHAR(20),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        
        # Create index for better query performance
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sensor_readings_timestamp 
            ON sensor_readings(timestamp DESC);
            """
        )
        
        cur.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sensor_readings_location 
            ON sensor_readings(location, timestamp DESC);
            """
        )
        
        print("[Consumer] ✓ Table 'sensor_readings' ready with indexes.")
        print("[Consumer] 🎧 Listening for messages...\n")

        message_count = 0
        for message in consumer:
            try:
                reading = message.value
                
                insert_query = """
                    INSERT INTO sensor_readings 
                    (sensor_id, sensor_type, location, value, timestamp, anomaly, unit)
                    VALUES (%s, %s, %s, %s, %s, %s, %s);
                """
                cur.execute(
                    insert_query,
                    (
                        reading["sensor_id"],
                        reading["sensor_type"],
                        reading["location"],
                        reading["value"],
                        reading["timestamp"],
                        reading["anomaly"],
                        reading["unit"],
                    ),
                )
                message_count += 1
                
                anomaly_flag = "⚠️" if reading["anomaly"] else "✓"
                print(f"[Consumer] {anomaly_flag} #{message_count} Stored: "
                      f"{reading['sensor_type']:<12} | "
                      f"{reading['value']:>8.2f} {reading['unit']:<4} | "
                      f"{reading['location']:<20}")
                
            except Exception as e:
                print(f"[Consumer ERROR] Failed to process message: {e}")
                continue
                
    except KeyboardInterrupt:
        print("\n[Consumer] Shutting down gracefully...")
    except Exception as e:
        print(f"[Consumer ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_consumer()
