from pyspark.sql.types import DoubleType, StringType, StructField, StructType, TimestampType

TABLE_NAME = 'anomaly_alerts'

COL_EQUIPMENT_ID = 'equipment_id'
COL_ALERT_TYPE = 'alert_type'
COL_VALUE = 'value'
COL_THRESHOLD = 'threshold'
COL_TIMESTAMP = 'timestamp'

SCHEMA = StructType([
    StructField(COL_EQUIPMENT_ID, StringType()),
    StructField(COL_ALERT_TYPE, StringType()),
    StructField(COL_VALUE, DoubleType()),
    StructField(COL_THRESHOLD, DoubleType()),
    StructField(COL_TIMESTAMP, TimestampType()),
])
