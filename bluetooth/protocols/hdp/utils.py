from datetime import datetime

AarqApduTag = 0xE200
AareApduTag = 0xE300
RlrqApduTag = 0xE400
RlreApduTag = 0xE500
AbrtApduTag = 0xE600
PrstApduTag = 0xE700


def s2b(msg):
    if msg is None:
        return None
    return [ord(x) for x in msg]


def b2s(msg):
    if msg is None:
        return None
    return "".join([chr(int(x)) for x in msg])


def int_u16(str):
    bytes = s2b(str)
    return (bytes[0] << 8) | bytes[1]


def float(str):
    bytes = s2b(str)
    exp = bytes[0]
    exp = signed(exp, 8)

    mantissa = (bytes[1] << 16) | (bytes[2] << 8) | bytes[3]
    mantissa = signed(mantissa, 24)
    result = mantissa * (10 ** exp)

    if exp < 0:
        return round(result, -exp)
    return result


def sfloat(str):
    bytes = s2b(str)
    exp = (bytes[0] & 0xF0) >> 4
    exp = signed(exp, 4)

    mantissa = ((bytes[0] & 0x0F) << 8) | bytes[1]
    mantissa = signed(mantissa, 12)
    result = mantissa * (10 ** exp)

    if exp < 0:
        return round(result, -exp)
    return result


def absolute_time(str):
    bytes = s2b(str)
    year = decode_bcd((bytes[0] << 8) | bytes[1], 4)
    month = decode_bcd(bytes[2], 2)
    day = decode_bcd(bytes[3], 2)
    hour = decode_bcd(bytes[4], 2)
    minute = decode_bcd(bytes[5], 2)
    second = decode_bcd(bytes[6], 2)
    sec_fractions = decode_bcd(bytes[7], 2)
    return int((datetime(year, month, day, hour, minute, second, sec_fractions * 10000) - datetime(1970, 1,
                                                                                                   1)).total_seconds()) * 1000


def signed(val, bits):
    """compute the 2's compliment of int value val"""
    if (val & (1 << (bits - 1))) != 0:  # if sign bit is set e.g., 8bit: 128-255
        val = val - (1 << bits)  # compute negative value
    return val  # return positive value as is


def decode_bcd(val, digits):
    decoded = 0
    for i in range(digits):
        decoded += ((val >> (i * 4)) & 0xF) * (10 ** i)
    return decoded
