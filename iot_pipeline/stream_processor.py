"""
Stream Processor with Windowed Aggregations
Simulates Apache Flink functionality using Python for easier deployment.

Features:
- 1-minute tumbling windows
- Real-time aggregations per location and sensor type
- Statistical anomaly detection using Z-scores
- Writes results to PostgreSQL
"""

import json
import time
from datetime import datetime, timedelta
from collections import defaultdict
from kafka import KafkaConsumer
import psycopg2
import numpy as np
from typing import Dict, List


class WindowedAggregator:
    """Manages time-based windowed aggregations for sensor data."""
    
    def __init__(self, window_size_seconds: int = 60):
        self.window_size = timedelta(seconds=window_size_seconds)
        self.windows = defaultdict(lambda: defaultdict(list))
        self.last_flush = datetime.now()
        
    def add_reading(self, reading: dict):
        """Add a reading to the appropriate window."""
        timestamp = datetime.fromisoformat(reading["timestamp"])
        window_key = self._get_window_key(timestamp)
        
        # Key by location and sensor_type
        group_key = (reading["location"], reading["sensor_type"])
        
        self.windows[window_key][group_key].append({
            "value": reading["value"],
            "anomaly": reading["anomaly"],
            "timestamp": timestamp,
        })
    
    def _get_window_key(self, timestamp: datetime) -> datetime:
        """Calculate which window this timestamp belongs to."""
        # Round down to the nearest minute
        return timestamp.replace(second=0, microsecond=0)
    
    def get_completed_windows(self, current_time: datetime) -> Dict:
        """Get windows that are complete and ready for aggregation."""
        completed = {}
        cutoff_time = current_time - self.window_size
        
        for window_start, groups in list(self.windows.items()):
            if window_start < cutoff_time:
                completed[window_start] = groups
                del self.windows[window_start]
        
        return completed
    
    def aggregate_window(self, window_start: datetime, groups: Dict) -> List[Dict]:
        """Compute aggregations for a completed window."""
        results = []
        window_end = window_start + self.window_size
        
        for (location, sensor_type), readings in groups.items():
            if not readings:
                continue
            
            values = [r["value"] for r in readings]
            anomaly_count = sum(1 for r in readings if r["anomaly"])
            
            # Calculate statistics
            avg_value = np.mean(values)
            min_value = np.min(values)
            max_value = np.max(values)
            stddev_value = np.std(values) if len(values) > 1 else 0.0
            count_readings = len(values)
            
            # Calculate Z-scores for anomaly detection
            if stddev_value > 0:
                z_scores = [(v - avg_value) / stddev_value for v in values]
                statistical_anomalies = sum(1 for z in z_scores if abs(z) > 3.0)
            else:
                statistical_anomalies = 0
            
            results.append({
                "window_start": window_start,
                "window_end": window_end,
                "location": location,
                "sensor_type": sensor_type,
                "avg_value": round(avg_value, 2),
                "min_value": round(min_value, 2),
                "max_value": round(max_value, 2),
                "stddev_value": round(stddev_value, 2),
                "count_readings": count_readings,
                "anomaly_count": anomaly_count,
                "statistical_anomalies": statistical_anomalies,
            })
        
        return results


def setup_database(conn):
    """Create tables for aggregated data."""
    cur = conn.cursor()
    
    # Create aggregates table
    cur.execute("""
        CREATE TABLE IF NOT EXISTS sensor_aggregates (
            id SERIAL PRIMARY KEY,
            window_start TIMESTAMP,
            window_end TIMESTAMP,
            location VARCHAR(100),
            sensor_type VARCHAR(50),
            avg_value NUMERIC(10, 2),
            min_value NUMERIC(10, 2),
            max_value NUMERIC(10, 2),
            stddev_value NUMERIC(10, 2),
            count_readings INTEGER,
            anomaly_count INTEGER,
            statistical_anomalies INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(window_start, location, sensor_type)
        );
    """)
    
    # Create index for better query performance
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_aggregates_window 
        ON sensor_aggregates(window_start DESC);
    """)
    
    cur.execute("""
        CREATE INDEX IF NOT EXISTS idx_aggregates_location 
        ON sensor_aggregates(location, window_start DESC);
    """)
    
    conn.commit()
    print("[Stream Processor] ✓ Aggregates table ready.")


def write_aggregates(conn, aggregates: List[Dict]):
    """Write aggregated results to PostgreSQL."""
    if not aggregates:
        return
    
    cur = conn.cursor()
    
    for agg in aggregates:
        try:
            cur.execute("""
                INSERT INTO sensor_aggregates 
                (window_start, window_end, location, sensor_type, 
                 avg_value, min_value, max_value, stddev_value,
                 count_readings, anomaly_count, statistical_anomalies)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (window_start, location, sensor_type) 
                DO UPDATE SET
                    avg_value = EXCLUDED.avg_value,
                    min_value = EXCLUDED.min_value,
                    max_value = EXCLUDED.max_value,
                    stddev_value = EXCLUDED.stddev_value,
                    count_readings = EXCLUDED.count_readings,
                    anomaly_count = EXCLUDED.anomaly_count,
                    statistical_anomalies = EXCLUDED.statistical_anomalies;
            """, (
                agg["window_start"],
                agg["window_end"],
                agg["location"],
                agg["sensor_type"],
                agg["avg_value"],
                agg["min_value"],
                agg["max_value"],
                agg["stddev_value"],
                agg["count_readings"],
                agg["anomaly_count"],
                agg["statistical_anomalies"],
            ))
        except Exception as e:
            print(f"[Stream Processor ERROR] Failed to write aggregate: {e}")
            continue
    
    conn.commit()


def run_stream_processor():
    """Main stream processor that mimics Flink windowed operations."""
    try:
        print("[Stream Processor] Connecting to Kafka at localhost:9092...")
        consumer = KafkaConsumer(
            "iot_sensors",
            bootstrap_servers="localhost:9092",
            auto_offset_reset="latest",
            enable_auto_commit=True,
            value_deserializer=lambda v: json.loads(v.decode("utf-8")),
            group_id="stream-processor-group",
        )
        print("[Stream Processor] ✓ Connected to Kafka successfully!")
        
        print("[Stream Processor] Connecting to PostgreSQL...")
        conn = psycopg2.connect(
            dbname="iot_db",
            user="iot_user",
            password="iot_password",
            host="localhost",
            port="5432",
        )
        conn.autocommit = False
        print("[Stream Processor] ✓ Connected to PostgreSQL successfully!")
        
        setup_database(conn)
        
        # Initialize windowed aggregator (1-minute windows)
        aggregator = WindowedAggregator(window_size_seconds=60)
        
        print("[Stream Processor] 🎧 Processing stream with 1-minute tumbling windows...\n")
        
        last_check = datetime.now()
        message_count = 0
        
        for message in consumer:
            try:
                reading = message.value
                aggregator.add_reading(reading)
                message_count += 1
                
                # Check for completed windows every 10 seconds
                current_time = datetime.now()
                if (current_time - last_check).total_seconds() >= 10:
                    completed_windows = aggregator.get_completed_windows(current_time)
                    
                    for window_start, groups in completed_windows.items():
                        aggregates = aggregator.aggregate_window(window_start, groups)
                        write_aggregates(conn, aggregates)
                        
                        if aggregates:
                            print(f"\n[Stream Processor] ⏰ Window completed: {window_start.strftime('%H:%M:%S')}")
                            for agg in aggregates:
                                anomaly_flag = "⚠️" if agg["anomaly_count"] > 0 else ""
                                print(f"  📊 {agg['location']:<20} | "
                                      f"{agg['sensor_type']:<12} | "
                                      f"Avg: {agg['avg_value']:>7.2f} | "
                                      f"Readings: {agg['count_readings']:>3} | "
                                      f"Anomalies: {agg['anomaly_count']} {anomaly_flag}")
                            print()
                    
                    last_check = current_time
                
                if message_count % 100 == 0:
                    print(f"[Stream Processor] Processed {message_count} messages...")
                
            except Exception as e:
                print(f"[Stream Processor ERROR] Failed to process message: {e}")
                continue
                
    except KeyboardInterrupt:
        print("\n[Stream Processor] Shutting down gracefully...")
        conn.close()
    except Exception as e:
        print(f"[Stream Processor ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise


if __name__ == "__main__":
    run_stream_processor()
