import dbus
import dbus.service
import glib
import io
import os
import socket
from dbus.mainloop.glib import DBusGMainLoop
from importlib import import_module

import firebase
from hdp.utils import *
from sensor import Sensor


def ChannelConnected(channel, interface, device):
    print "Device %s channel %s up" % (device, channel)
    channel = bus.get_object("org.bluez", channel)
    channel = dbus.Interface(channel, "org.bluez.HealthChannel1")
    properties_manager = dbus.Interface(channel, 'org.freedesktop.DBus.Properties')
    # Create application -> "data received"
    # print self.plugin["Spec"]
    fd = channel.Acquire()
    print "Got raw rd %s" % fd
    # take fd ownership
    fd = fd.take()
    print "FD number is %d" % fd
    # encapsulate numeric fd in Python socket object
    sk = socket.fromfd(fd, socket.AF_UNIX, socket.SOCK_STREAM)
    # fromfd() does dup() so we need to close the original
    os.close(fd)
    print "FD acquired"
    # get mapped  method
    app = properties_manager.Get('org.bluez.HealthChannel1', 'Application')
    assert bluez_app_sensor_map.has_key(app)
    sensor = bluez_app_sensor_map[app]
    glib.io_add_watch(sk, watch_bitmap, sensor.data_received)


def ChannelDeleted(channel, interface, device):
    print "Device %s channel %s deleted" % (device, channel)


DBusGMainLoop(set_as_default=True)
bus = dbus.SystemBus()
watch_bitmap = glib.IO_IN | glib.IO_ERR | glib.IO_HUP | glib.IO_NVAL
bus.add_signal_receiver(ChannelConnected,
                        signal_name="ChannelConnected",
                        bus_name="org.bluez",
                        path_keyword="device",
                        interface_keyword="interface",
                        dbus_interface="org.bluez.HealthDevice1")

bus.add_signal_receiver(ChannelDeleted,
                        signal_name="ChannelDeleted",
                        bus_name="org.bluez",
                        path_keyword="device",
                        interface_keyword="interface",
                        dbus_interface="org.bluez.HealthDevice1")

bluez_app_sensor_map = {}


class HDP(Sensor):
    def __init__(self, plugin):
        global bus
        self.plugin = plugin
        self.fb = None
        self.plugin_name = self.plugin["SensorName"]
        spec_module_name = "bluetooth.protocols.hdp.{0}".format(str.lower(self.plugin["SensorName"].replace('-', '_')))
        mod = import_module(spec_module_name)
        self.parse_attribute = getattr(mod, "parse_attribute")

        self.is_subscribed = False
        self.measurements = {}

        self.config = {"Role": "Sink", "DataType": dbus.types.UInt16(self.plugin["MDEPDataType"])}
        self.manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"),
                                      "org.bluez.HealthManager1")

    def measurement_received(self, measurements):
        if self.fb is None:
            self.fb = firebase.Firebase()
        return self.fb.send(measurements, plugin=self.plugin)

    def data_received(self, sk, evt):
        data = None
        if evt & glib.IO_IN:
            try:
                data = sk.recv(1024)
            except IOError as e:
                data = ""
            if data:
                print "Data received {0}".format(self.plugin["SensorName"])
                response = self.parse_message(data, self.measurement_received)
                if response:
                    try:
                        sk.send(response)
                    except socket.error:
                        pass

                        # print "Response sent"

        more = (evt == glib.IO_IN and data)

        if not more:
            # print "EOF"
            try:
                sk.shutdown(2)
            except IOError:
                pass
            sk.close()
            # self.single_measurement_loop.quit()

        return more

    def parse_message(self, msg, measurements_received_cb):
        resp = None

        stream = io.BytesIO(msg)

        apdu_type = int_u16(stream.read(2))
        if apdu_type == AarqApduTag:
            system_id = [0] * 8
            ma_bytes = []

            for i in range(len(msg)):
                ma_bytes.append(ord(msg[i]))

            for i in range(8):
                system_id[i] = ord(msg[36 + i])

            oui = system_id[0] << 16 | system_id[1] << 8 | system_id[2]
            if not oui == self.plugin["OUI"]:
                print "OUI not as expected. Will not associate"
                resp = (
                    0xe3, 0x00,  # APDU CHOICE Type(AareApdu)
                    0x00, 0x2c,  # CHOICE.length = 44
                    0x00, 0x06,  # result=rejected=unknown
                    0x00, 0x00,  # data-proto-id = 0
                    0x00, 0x26,  # data-proto-info length = 38
                    0x80, 0x00, 0x00, 0x00,  # protocolVersion
                    0x80, 0x00,  # encoding rules = MDER
                    0x80, 0x00, 0x00, 0x00,  # nomenclatureVersion
                    0x00, 0x00, 0x00, 0x00,  # functionalUnits, normal Association
                    0x80, 0x00, 0x00, 0x00,  # systemType = sys-type-manager
                    0x00, 0x08,  # system-id length = 8 and value (manufacturer- and device- specific)
                    int(system_id[0]), int(system_id[1]), int(system_id[2]), int(system_id[3]), int(system_id[4]),
                    int(system_id[5]), int(system_id[6]), int(system_id[7]),
                    0x00, 0x00,  # Manager's response to config-id is always 0
                    0x00, 0x00,  # Manager's response to data-req-mode-flags is always 0
                    0x00, 0x00,  # data-req-init-agent-count and data-req-init-manager-count are always 0
                    0x00, 0x00, 0x00, 0x00,  # optionList.count = 0 | optionList.length = 0
                )
            else:
                # print 'IEEE association request\n'
                resp = (
                    0xe3, 0x00,  # APDU CHOICE Type(AareApdu)
                    0x00, 0x2c,  # CHOICE.length = 44
                    0x00, 0x00,  # result=accept
                    0x50, 0x79,  # data-proto-id = 20601
                    0x00, 0x26,  # data-proto-info length = 38
                    0x80, 0x00, 0x00, 0x00,  # protocolVersion
                    0x80, 0x00,  # encoding rules = MDER
                    0x80, 0x00, 0x00, 0x00,  # nomenclatureVersion
                    0x00, 0x00, 0x00, 0x00,  # functionalUnits, normal Association
                    0x80, 0x00, 0x00, 0x00,  # systemType = sys-type-manager
                    0x00, 0x08,  # system-id length = 8 and value (manufacturer- and device- specific)
                    int(system_id[0]), int(system_id[1]), int(system_id[2]), int(system_id[3]), int(system_id[4]),
                    int(system_id[5]), int(system_id[6]), int(system_id[7]),
                    0x00, 0x00,  # Manager's response to config-id is always 0
                    0x00, 0x00,  # Manager's response to data-req-mode-flags is always 0
                    0x00, 0x00,  # data-req-init-agent-count and data-req-init-manager-count are always 0
                    0x00, 0x00, 0x00, 0x00,  # optionList.count = 0 | optionList.length = 0
                )

        elif apdu_type == PrstApduTag:
            # print 'IEEE agent data\n'
            resp = (
                0xe7, 0x00,  # APDU CHOICE Type(PrstApdu)
                0x00, 0x12,  # CHOICE.length = 18
                0x00, 0x10,  # OCTET STRING.length = 16
                ord(msg[6]), ord(msg[7]),  # invoke-id (mirrored from invocation)
                0x02, 0x01,  # CHOICE(Remote Operation Response | Confirmed Event Report)
                0x00, 0x0a,  # CHOICE.length = 10
                0x00, 0x00,  # obj-handle = 0 (MDS object)
                0x00, 0x00, 0x00, 0x00,  # currentTime = 0
                0x0d, 0x1f,  # event-type = MDC_NOTI_SCAN_REPORT_MP_FIXED
                0x00, 0x00,  # event-reply-info.length = 0
            )

            # bytes 26-27, ScanReportInfoMPFixed.scn-per-fixed.length : number of measurements
            stream.seek(26)
            num_measurements = int_u16(stream.read(2))
            stream.read(2)  # ScanReportInfoMPFixed.scan-per-fixed.length
            if num_measurements >= 1:
                self.measurements = {}
                person = stream.read(2)[1]
                num_attributes = int_u16(
                    stream.read(2))  # ScanReportInfoMPFixed.scan-per-fixed.value[i].obs-scan-fixed.count
                stream.read(2)  # ScanReportInfoMPFixed.scan-per-fixed.value[0].obs-scan-fixed.length

                # measurements['Person'] = person
                for _ in range(num_attributes):
                    obj_handle = int_u16(stream.read(
                        2))  # ScanReportInfoMPFixed.scan-per-fixed.value[i].obs-scan-fixed.value[j].obj-handle = 1
                    length = int_u16(stream.read(
                        2))  # ScanReportInfoMPFixed.scan-per-fixed.value[i].obs-scan-fixed.value[j].obs-val-data.length
                    data = stream.read(
                        length)  # ScanReportInfoMPFixed.scan-per-fixed.value[i].obs-scan-fixed.value[j].obs-val-data
                    measurement = self.parse_attribute(obj_handle, data)
                    if not measurement is None:
                        val = measurement['Value']
                        if isinstance(val, list):
                            for i in range(len(val)):
                                idx = "{0}_{1}".format(obj_handle, i)
                                temp_measurement = {}
                                temp_measurement['Value'] = measurement['Value'][i]
                                temp_measurement['Time'] = measurement['Time']
                                self.measurements[idx] = temp_measurement
                        else:
                            self.measurements[obj_handle] = measurement

            if not self.measurements == {}:
                measurements_received_cb(self.measurements)


        elif apdu_type == RlrqApduTag:
            # print 'Association release request\n'
            resp = (
                0xe5, 0x00,  # APDU CHOICE Type(RlreApdu)
                0x00, 0x02,  # CHOICE.length = 2
                0x00, 0x00  # reason = normal
            )

        # print "outgoing message: "+str(resp)+'\n'
        return b2s(resp)

    def subscribe(self):
        global bluez_app_sensor_map

        if not self.is_subscribed:
            self.is_subscribed = True
            self.app = self.manager.CreateApplication(self.config)
            bluez_app_sensor_map[self.app] = self

    def unsubscribe(self):
        global bluez_app_sensor_map

        if self.is_subscribed:
            self.is_subscribed = False
            self.manager.DestroyApplication(self.app)
            del bluez_app_sensor_map[self.app]
