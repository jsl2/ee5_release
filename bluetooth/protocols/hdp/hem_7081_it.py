from utils import *

BloodPressureHandle = 1
PulseRateHandle = 2


def parse_attribute(obj_handle, data):
    value = None
    timestamp = 0

    if obj_handle == BloodPressureHandle:
        # Systolic, Diastolic and Mean
        value = [sfloat(data[4:6]), sfloat(data[6:8]), sfloat(data[8:10])]
        timestamp = absolute_time(data[10:18])
    elif obj_handle == PulseRateHandle:
        value = sfloat(data[0:2])
        timestamp = absolute_time(data[2:10])

    if not value == None:
        return {'Value': value, 'Time': timestamp}
    else:
        return None
