from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

TABLE_NAME = 'enriched_telemetry'

COL_EQUIPMENT_ID = 'equipment_id'
COL_DEVICE_TYPE = 'device_type'
COL_MANUFACTURER = 'manufacturer'
COL_SITE_NAME = 'site_name'
COL_REGION = 'region'
COL_TEMPERATURE = 'temperature'
COL_VIBRATION = 'vibration'
COL_PRESSURE = 'pressure'
COL_TIMESTAMP = 'timestamp'

SCHEMA = StructType([
    StructField(COL_EQUIPMENT_ID, StringType()),
    StructField(COL_DEVICE_TYPE, StringType()),
    StructField(COL_MANUFACTURER, StringType()),
    StructField(COL_SITE_NAME, StringType()),
    StructField(COL_REGION, StringType()),
    StructField(COL_TEMPERATURE, DoubleType()),
    StructField(COL_VIBRATION, DoubleType()),
    StructField(COL_PRESSURE, DoubleType()),
    StructField(COL_TIMESTAMP, TimestampType()),
])
