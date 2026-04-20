from pyspark.sql.types import DoubleType, LongType, StringType, StructField, StructType

TABLE_NAME = 'equipment_metrics'

COL_EQUIPMENT_ID = 'equipment_id'
COL_DEVICE_TYPE = 'device_type'
COL_AVG_TEMPERATURE = 'avg_temperature'
COL_AVG_VIBRATION = 'avg_vibration'
COL_AVG_PRESSURE = 'avg_pressure'
COL_READING_COUNT = 'reading_count'

SCHEMA = StructType([
    StructField(COL_EQUIPMENT_ID, StringType()),
    StructField(COL_DEVICE_TYPE, StringType()),
    StructField(COL_AVG_TEMPERATURE, DoubleType()),
    StructField(COL_AVG_VIBRATION, DoubleType()),
    StructField(COL_AVG_PRESSURE, DoubleType()),
    StructField(COL_READING_COUNT, LongType()),
])
