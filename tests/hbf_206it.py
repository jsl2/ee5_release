import random
import time
import unittest

import yaml

import gateway
from bluetooth.protocols.hdp_sensor import HDP


class TestHbf206It(unittest.TestCase):
    def setUp(self):
        self.plugin_path = "../plugins/HBF-206IT.json"
        gateway.instance = gateway.Gateway()
        current_timestamp = int(time.time()) * 1000
        self.measurements = {
            # Weight
            1: {
                "Time": current_timestamp,
                "Value": 93 + round(4 * random.random(), 1)
            },
            # BMI (Will be redundant)
            3: {
                "Time": current_timestamp,
                "Value": 30 + round(2 * random.random(), 1)
            },
            # Body Fat Rate
            4: {
                "Time": current_timestamp,
                "Value": 27 + round(3 * random.random(), 1)
            },
            # Basal Metabolism
            5: {
                "Time": current_timestamp,
                "Value": 2000000 + round(50000 * random.random())
            },
            # Visceral Fat Level
            6: {
                "Time": current_timestamp,
                "Value": 8 + round(3 * random.random())
            },
            # Body Age
            7: {
                "Time": current_timestamp,
                "Value": 25
            },
            # Skeletal Muscle Rate
            8: {
                "Time": current_timestamp,
                "Value": 33 + round(6 * random.random(), 1)
            }
        }

        # Wireshark capture of measurements for testing parse message
        self.measurements_message = ''.join(chr(x) for x in
                                            [0xe7, 0x00, 0x00, 0xc6, 0x00, 0xc4, 0x00, 0x01, 0x01, 0x01, 0x00, 0xbe,
                                             0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0x0d, 0x1f, 0x00, 0xb4, 0xf0, 0x00,
                                             0x00, 0x01, 0x00, 0x01, 0x00, 0xac, 0x00, 0x31, 0x00, 0x0a, 0x00, 0xa6,
                                             0x00, 0x01, 0x00, 0x0c, 0xff, 0x00, 0x02, 0xe2, 0x20, 0x17, 0x02, 0x26,
                                             0x16, 0x21, 0x00, 0x00, 0x00, 0x02, 0x00, 0x0c, 0xff, 0x00, 0x06, 0xd6,
                                             0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00, 0x00, 0x03, 0x00, 0x0c,
                                             0xff, 0x00, 0x00, 0xf1, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00,
                                             0x00, 0x04, 0x00, 0x0c, 0xff, 0x00, 0x00, 0xc9, 0x20, 0x17, 0x02, 0x26,
                                             0x16, 0x21, 0x00, 0x00, 0x00, 0x05, 0x00, 0x0c, 0x03, 0x00, 0x06, 0xe8,
                                             0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00, 0x00, 0x06, 0x00, 0x0a,
                                             0xf0, 0x32, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00, 0x00, 0x07,
                                             0x00, 0x0a, 0x00, 0x18, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00,
                                             0x00, 0x08, 0x00, 0x14, 0x00, 0x04, 0x00, 0x08, 0xf1, 0xaa, 0x00, 0x00,
                                             0x00, 0x00, 0x00, 0x00, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00,
                                             0x00, 0x09, 0x00, 0x0a, 0x00, 0x00, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21,
                                             0x00, 0x00, 0x00, 0x0a, 0x00, 0x10, 0x00, 0x02, 0x00, 0x04, 0x00, 0x00,
                                             0x00, 0x16, 0x20, 0x17, 0x02, 0x26, 0x16, 0x21, 0x00, 0x00, 0x34, 0xa2])

    def test_load_plugin_send_measurements(self):
        # Evgeniy
        user = "r0479950"
        with open(self.plugin_path) as plugin_file:
            plugin = yaml.safe_load(plugin_file)
            gateway.instance.validate_plugin(plugin)
            gateway.instance.firebase_plugin_setup(plugin)

            gateway.instance.fb.send(self.measurements, plugin, user)

    def test_parse_message(self):
        """Tests using measurement_message from wireshark capture.
        Expected results:
        1 Weight=73.8
        3 BMI=24.1
        4 Body Fat Rate=20.1
        5 Basal Metabolism = 1768000
        6 Visceral Fat Level = 5.0%
        7 Body Age = 24
        8 Skeletal Muscle Rate Whole Body = 42.6%
        """

        with open(self.plugin_path) as plugin_file:
            hdp = HDP(yaml.safe_load(plugin_file))

        def cb(measurements):
            self.assertEqual(measurements[1]['Value'], 73.8)
            self.assertEqual(measurements[3]['Value'], 24.1)
            self.assertEqual(measurements[4]['Value'], 20.1)
            self.assertEqual(measurements[5]['Value'], 1768000)
            self.assertEqual(measurements[6]['Value'], 5.0)
            self.assertEqual(measurements[7]['Value'], 24)
            self.assertEqual(measurements[8]['Value'], 42.6)

        hdp.parse_message(self.measurements_message, cb)


if __name__ == '__main__':
    unittest.main()
