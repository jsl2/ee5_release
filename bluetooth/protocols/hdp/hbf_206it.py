from utils import *

WeightHandle = 1
HeightHandle = 2
BodyMassIndexHandle = 3
BodyFatRateHandle = 4
BasalMetabolismHandle = 5
VisceralFatLevelHandle = 6
BodyAgeHandle = 7
SkeletalMuscleRateHandle = 8

FloatTimestampHandles = {WeightHandle, BodyMassIndexHandle, BodyFatRateHandle, BasalMetabolismHandle}
SFloatTimestampHandles = {VisceralFatLevelHandle, BodyAgeHandle}


def parse_attribute(obj_handle, data):
    value = None
    timestamp = 0

    if obj_handle in FloatTimestampHandles:
        value = float(data[0:4])
        timestamp = absolute_time(data[4:12])
    elif obj_handle in SFloatTimestampHandles:
        value = sfloat(data[0:2])
        timestamp = absolute_time(data[2:10])
    elif obj_handle == SkeletalMuscleRateHandle:
        # SkeletalMuscleRate is a special case (SEQUENCE OF SFLOAT)
        value = sfloat(data[4:6])
        timestamp = absolute_time(data[12:20])

    if not value == None:
        return {'Value': value, 'Time': timestamp}
    else:
        return None
