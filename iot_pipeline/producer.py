import time
import json
import uuid
import random
from datetime import datetime
from kafka import KafkaProducer
import numpy as np

class IoTSensorSimulator:
    """Simulates realistic IoT environmental sensors with various patterns."""
    
    def __init__(self, sensor_id: str, sensor_type: str, location: str):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.location = location
        
        # Base values for realistic data
        self.base_values = {
            "temperature": 22.0,  # Celsius
            "humidity": 60.0,     # Percentage
            "air_quality": 50.0,  # AQI (Air Quality Index)
            "pressure": 1013.25,  # hPa
            "co2": 400.0,         # ppm
        }
        
        # Add location-specific variations
        location_offsets = {
            "Server Room": {"temperature": 3.0, "humidity": -15.0, "co2": 50.0},
            "Office Floor 3": {"temperature": 0.5, "humidity": 5.0, "co2": 100.0},
            "Warehouse": {"temperature": -2.0, "humidity": 10.0, "air_quality": 10.0},
            "Laboratory": {"temperature": 1.0, "humidity": -5.0, "co2": 80.0},
            "Manufacturing": {"temperature": 2.5, "humidity": 0.0, "air_quality": 15.0},
        }
        
        if location in location_offsets:
            for key, offset in location_offsets[location].items():
                if key in self.base_values:
                    self.base_values[key] += offset
        
        # Trend state (simulates slow drift over time)
        self.trend = 0.0
        self.trend_direction = random.choice([-1, 1])
        
    def generate_reading(self) -> dict:
        """Generate a single sensor reading with realistic patterns."""
        
        # Time-based patterns (daily cycles)
        hour = datetime.now().hour
        time_factor = np.sin(2 * np.pi * hour / 24)  # Daily cycle
        
        # Update slow trend
        self.trend += self.trend_direction * random.uniform(0.001, 0.01)
        if abs(self.trend) > 2.0:  # Reverse direction if drift is too much
            self.trend_direction *= -1
        
        # Generate readings based on sensor type
        value = self.base_values[self.sensor_type]
        
        # Add time-based variation
        if self.sensor_type == "temperature":
            value += time_factor * 3.0  # ±3°C daily variation
            noise = random.gauss(0, 0.5)
        elif self.sensor_type == "humidity":
            value += time_factor * 10.0  # ±10% daily variation
            noise = random.gauss(0, 2.0)
        elif self.sensor_type == "air_quality":
            value += time_factor * 15.0  # AQI varies more
            noise = random.gauss(0, 5.0)
        elif self.sensor_type == "pressure":
            value += time_factor * 5.0  # Pressure varies slowly
            noise = random.gauss(0, 1.0)
        elif self.sensor_type == "co2":
            value += time_factor * 100.0  # CO2 varies with occupancy
            noise = random.gauss(0, 10.0)
        else:
            noise = random.gauss(0, 1.0)
        
        # Add trend and noise
        value += self.trend + noise
        
        # Occasionally inject anomalies (5% chance)
        if random.random() < 0.05:
            anomaly_factor = random.uniform(1.5, 3.0)
            value *= anomaly_factor
            anomaly = True
        else:
            anomaly = False
        
        # Ensure realistic bounds
        if self.sensor_type == "temperature":
            value = max(-10.0, min(50.0, value))
        elif self.sensor_type == "humidity":
            value = max(0.0, min(100.0, value))
        elif self.sensor_type == "air_quality":
            value = max(0.0, min(500.0, value))
        elif self.sensor_type == "pressure":
            value = max(950.0, min(1050.0, value))
        elif self.sensor_type == "co2":
            value = max(300.0, min(2000.0, value))
        
        return {
            "sensor_id": self.sensor_id,
            "sensor_type": self.sensor_type,
            "location": self.location,
            "value": round(value, 2),
            "timestamp": datetime.now().isoformat(),
            "anomaly": anomaly,
            "unit": self._get_unit(),
        }
    
    def _get_unit(self) -> str:
        """Return the measurement unit for the sensor type."""
        units = {
            "temperature": "°C",
            "humidity": "%",
            "air_quality": "AQI",
            "pressure": "hPa",
            "co2": "ppm",
        }
        return units.get(self.sensor_type, "unknown")


def create_sensor_fleet() -> list:
    """Create a fleet of IoT sensors across different locations."""
    locations = ["Server Room", "Office Floor 3", "Warehouse", "Laboratory", "Manufacturing"]
    sensor_types = ["temperature", "humidity", "air_quality", "pressure", "co2"]
    
    sensors = []
    for location in locations:
        for sensor_type in sensor_types:
            sensor_id = f"{location.replace(' ', '_')}_{sensor_type}_{uuid.uuid4().hex[:6]}"
            sensors.append(IoTSensorSimulator(sensor_id, sensor_type, location))
    
    return sensors


def run_producer():
    """Kafka producer that sends IoT sensor readings to the 'iot_sensors' topic."""
    try:
        print("[Producer] Connecting to Kafka at localhost:9092...")
        producer = KafkaProducer(
            bootstrap_servers="localhost:9092",
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            request_timeout_ms=30000,
            max_block_ms=60000,
            retries=5,
        )
        print("[Producer] ✓ Connected to Kafka successfully!")
        
        # Create sensor fleet
        sensors = create_sensor_fleet()
        print(f"[Producer] ✓ Created {len(sensors)} virtual sensors")
        print(f"[Producer] 📡 Starting sensor data stream...\n")
        
        count = 0
        while True:
            # Each cycle, random sensors send readings (simulate async nature)
            active_sensors = random.sample(sensors, k=random.randint(5, 15))
            
            for sensor in active_sensors:
                reading = sensor.generate_reading()
                
                # Send to Kafka
                future = producer.send("iot_sensors", value=reading)
                
                # Log the reading
                anomaly_flag = "⚠️ ANOMALY" if reading["anomaly"] else ""
                print(f"[Producer] 📊 {reading['sensor_id'][:30]:<30} | "
                      f"{reading['sensor_type']:<12} | "
                      f"{reading['value']:>8.2f} {reading['unit']:<4} | "
                      f"{reading['location']:<20} {anomaly_flag}")
                
                count += 1
            
            producer.flush()
            
            # Variable sleep time (0.5 to 2 seconds between batches)
            sleep_time = random.uniform(0.5, 2.0)
            time.sleep(sleep_time)
            
    except KeyboardInterrupt:
        print("\n[Producer] Shutting down gracefully...")
    except Exception as e:
        print(f"[Producer ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_producer()
