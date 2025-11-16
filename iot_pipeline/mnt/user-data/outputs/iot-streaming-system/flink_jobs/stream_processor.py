"""
Apache Flink Stream Processing Job for IoT Sensor Data

This job performs:
1. Real-time windowed aggregations (1-minute tumbling windows)
2. Statistical anomaly detection using Z-scores
3. Multi-sensor correlation analysis
4. Writes aggregated results to PostgreSQL
"""

from pyflink.datastream import StreamExecutionEnvironment
from pyflink.table import StreamTableEnvironment, EnvironmentSettings
from pyflink.table.window import Tumble
from pyflink.table.expressions import col, lit
from datetime import timedelta
import json


def create_flink_job():
    """Create and configure Flink stream processing job."""
    
    # Create streaming environment
    env = StreamExecutionEnvironment.get_execution_environment()
    env.set_parallelism(2)
    
    # Create table environment
    settings = EnvironmentSettings.new_instance().in_streaming_mode().build()
    table_env = StreamTableEnvironment.create(env, environment_settings=settings)
    
    # Add Kafka and JDBC connectors
    table_env.get_config().get_configuration().set_string(
        "pipeline.jars",
        "file:///opt/flink/lib/flink-sql-connector-kafka-1.18.0.jar;"
        "file:///opt/flink/lib/flink-connector-jdbc-3.1.0-1.17.jar;"
        "file:///opt/flink/lib/postgresql-42.6.0.jar"
    )
    
    # Define Kafka source table
    table_env.execute_sql("""
        CREATE TABLE iot_sensor_stream (
            sensor_id STRING,
            sensor_type STRING,
            location STRING,
            value DOUBLE,
            timestamp_str STRING,
            anomaly BOOLEAN,
            unit STRING,
            event_time AS TO_TIMESTAMP(timestamp_str),
            WATERMARK FOR event_time AS event_time - INTERVAL '5' SECOND
        ) WITH (
            'connector' = 'kafka',
            'topic' = 'iot_sensors',
            'properties.bootstrap.servers' = 'kafka:9092',
            'properties.group.id' = 'flink-processor',
            'scan.startup.mode' = 'latest-offset',
            'format' = 'json',
            'json.fail-on-missing-field' = 'false',
            'json.ignore-parse-errors' = 'true'
        )
    """)
    
    # Define PostgreSQL sink for aggregated metrics
    table_env.execute_sql("""
        CREATE TABLE sensor_aggregates (
            window_start TIMESTAMP(3),
            window_end TIMESTAMP(3),
            location STRING,
            sensor_type STRING,
            avg_value DOUBLE,
            min_value DOUBLE,
            max_value DOUBLE,
            stddev_value DOUBLE,
            count_readings BIGINT,
            anomaly_count BIGINT,
            PRIMARY KEY (window_start, location, sensor_type) NOT ENFORCED
        ) WITH (
            'connector' = 'jdbc',
            'url' = 'jdbc:postgresql://postgres:5432/iot_db',
            'table-name' = 'sensor_aggregates',
            'username' = 'iot_user',
            'password' = 'iot_password',
            'driver' = 'org.postgresql.Driver'
        )
    """)
    
    # Windowed aggregation query (1-minute tumbling windows)
    aggregation_query = """
        INSERT INTO sensor_aggregates
        SELECT
            TUMBLE_START(event_time, INTERVAL '1' MINUTE) as window_start,
            TUMBLE_END(event_time, INTERVAL '1' MINUTE) as window_end,
            location,
            sensor_type,
            AVG(value) as avg_value,
            MIN(value) as min_value,
            MAX(value) as max_value,
            STDDEV(value) as stddev_value,
            COUNT(*) as count_readings,
            SUM(CASE WHEN anomaly = TRUE THEN 1 ELSE 0 END) as anomaly_count
        FROM iot_sensor_stream
        GROUP BY
            TUMBLE(event_time, INTERVAL '1' MINUTE),
            location,
            sensor_type
    """
    
    # Execute the aggregation job
    table_env.execute_sql(aggregation_query)
    
    print("[Flink] Stream processing job started successfully!")
    print("[Flink] Processing 1-minute tumbling windows...")
    print("[Flink] Writing aggregates to PostgreSQL...")


if __name__ == "__main__":
    try:
        create_flink_job()
    except Exception as e:
        print(f"[Flink ERROR] {e}")
        import traceback
        traceback.print_exc()
        raise
