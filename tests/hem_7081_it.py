import unittest

import yaml

from bluetooth.protocols.hdp_sensor import HDP


class TestHem7081It(unittest.TestCase):
    def setUp(self):
        self.plugin_path = "../plugins/HEM-7081-IT.json"
        # Wireshark capture of measurements for testing parse message
        self.measurements_message = ''.join(chr(x) for x in
                                            [0xe7, 0x00, 0x00, 0x52, 0x00, 0x50, 0x00, 0x01, 0x01, 0x01, 0x00, 0x4a,
                                             0x00, 0x00, 0xff, 0xff, 0xff, 0xff, 0x0d, 0x1f, 0x00, 0x40, 0xf0, 0x00,
                                             0x00, 0x01, 0x00, 0x01, 0x00, 0x38, 0x00, 0x41, 0x00, 0x03, 0x00, 0x32,
                                             0x00, 0x01, 0x00, 0x12, 0x00, 0x03, 0x00, 0x06, 0x00, 0x6d, 0x00, 0x39,
                                             0x00, 0x4a, 0x20, 0x17, 0x05, 0x12, 0x09, 0x30, 0x25, 0x00, 0x00, 0x02,
                                             0x00, 0x0a, 0x00, 0x32, 0x20, 0x17, 0x05, 0x12, 0x09, 0x30, 0x25, 0x00,
                                             0x00, 0x03, 0x00, 0x0a, 0x00, 0x00, 0x20, 0x17, 0x05, 0x12, 0x09, 0x30,
                                             0x25, 0x00])

    def test_parse_message(self):
        """Tests using measurement_message from wireshark capture.
        Expected results:
        1: Blood pressure
         .1 - Systolic: 109
         .2 - Diastolic: 57
         .3 - Mean: 74
        2 HR=50
        """

        with open(self.plugin_path) as plugin_file:
            hdp = HDP(yaml.safe_load(plugin_file))

        def cb(measurements):
            self.assertEqual(measurements["1_0"]['Value'], 109)
            self.assertEqual(measurements["1_1"]['Value'], 57)
            self.assertEqual(measurements["1_2"]['Value'], 74)
            self.assertEqual(measurements["2"]['Value'], 50)

        hdp.parse_message(self.measurements_message, cb)


if __name__ == '__main__':
    unittest.main()
