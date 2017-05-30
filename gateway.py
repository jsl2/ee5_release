"""Main gateway script to run on raspberry pi.
Monitors available sensor configurations and sends results to firebase.

Sensor modules are loaded at runtime depending on configuration.
All sensors must have a 'monitor' method, which when run will asynchronously to monitor
the sensor for measurements and send results to firebase.
"""
import gobject
import hashlib
import inspect
import logging
import os
import threading
from dbus.mainloop.glib import DBusGMainLoop
from importlib import import_module
from threading import Thread

import yaml

import Last_tagged_user
import firebase
from errors import PluginError
from sensor import Sensor


class Gateway(object):
    REQUIRED_PLUGIN_KEYS = {"SensorName", "ConnectionType", "Protocol", "Handles", "Configs"}

    plugins = {}

    def __init__(self):
        self.fb = firebase.Firebase()
        self.dir_path = os.path.dirname(os.path.realpath(__file__))
        self.logger = logging.getLogger("Gateway")
        self.logger.setLevel(logging.DEBUG)

        # create console handler and set level to debug
        ch = logging.StreamHandler()
        ch.setLevel(logging.DEBUG)

        # create formatter
        formatter = logging.Formatter('%(name)s: %(levelname)s - %(message)s')

        # add formatter to ch
        ch.setFormatter(formatter)

        if not self.logger.handlers:
            self.logger.addHandler(ch)

    def parse_plugins(self):
        """Loads all configs from the /plugins directory and instantiates sensor
        objects for each plugin.

        Returns:
            list: sensor objects
        """
        sensors = []
        plugin_path = os.path.join(self.dir_path, "plugins")
        for plugin_filename in os.listdir(plugin_path):
            plugin_full_path = os.path.join(plugin_path, plugin_filename)
            self.logger.debug("Loading {0}".format(plugin_filename))
            plugin = self.parse_plugin(plugin_full_path)
            if plugin is not None:
                sensors.append(plugin)

        if sensors == []:
            return None

        return sensors

    def parse_plugin(self, plugin_path):
        with open(plugin_path) as plugin_file:
            plugin = yaml.safe_load(plugin_file)

            try:
                self.validate_plugin(plugin)
            except PluginError as e:
                self.logger.error("Plugin {0} invalid.".format(plugin_path))
                self.logger.exception(e)
                return None

            self.firebase_plugin_setup(plugin)

            conn = str.lower(plugin["ConnectionType"])
            protocol = str.lower(plugin["Protocol"])
            module_name = "{0}.protocols.{1}_sensor".format(conn, protocol)

            try:
                module = import_module(module_name)
            except ImportError:
                self.logger.error(
                    "Plugin {0} failed to load: {1} not found".format(plugin_path, module_name))
                return None

            try:
                sensor_class = getattr(module, protocol.upper())
            except AttributeError:
                self.logger.error(
                    "Plugin {0} failed to load: sensor class {1} not found in {2}".format(plugin_path,
                                                                                          protocol.upper(),
                                                                                          module_name))
                return None

            assert inspect.isclass(sensor_class)
            # sensor_class args: plugin
            try:
                return sensor_class(plugin)
            except ImportError:
                self.logger.error(
                    "Plugin {0} failed to load: spec {1} not found".format(plugin_path, plugin["Spec"]))
                return None
            except AttributeError as e:
                print e
                return None

    def validate_plugin(self, plugin):
        """Todo: Validate a given plugin json.
        Args:
            plugin (dict): Plugin dictionary to validate

        Returns:
            bool: is configuration valid?
        """
        for key in Gateway.REQUIRED_PLUGIN_KEYS:
            if key not in plugin.keys():
                raise PluginError("Required plugin key {0} not found".format(key))

        if not plugin["ConnectionType"] == "Bluetooth":
            raise PluginError("Currently only bluetooth plugins are supported!")

    def firebase_plugin_setup(self, plugin):
        """Todo: Check firebase is ready to work with given plugin.
        If not, firebase will be initialised.
            1) Check if Sensor with key = md5 hash of SensorName exists
                a) If not create Sensor table with key of the MD5 hash:
                   ConnectionType, SensorName and Series (Type & Weight)
            2) For each config, check if Config with key = md5 hash of the
               stringified config exists.
                a) If not create config 

        Args:
            plugin (dict): Validated plugin dictionary

        Returns:
            None
        """
        sensor_key = self.setup_sensor(plugin)
        self.setup_configs(plugin, sensor_key)

    def setup_sensor(self, plugin):
        sensor_hash = hashlib.md5(plugin['SensorName']).hexdigest()
        sensor_result = self.fb.db.child("SensorsF").child(sensor_hash).get()
        if not sensor_result.val():
            self.logger.debug("Sensor {0} does not exist on firebase. Creating with key {1}".format(plugin[
                                                                                                        'SensorName'],
                                                                                                    sensor_hash))
            sensor = {
                "ConnectionType": plugin['ConnectionType'],
                "SensorName": plugin['SensorName'],
                "Series": {}
            }
            for handle_name, handle in plugin['Handles'].iteritems():
                handle_name = "S{0}".format(handle_name)
                sensor["Series"][handle_name] = {}
                sensor["Series"][handle_name]["Type"] = handle["Measurement"]
                sensor["Series"][handle_name]["Unit"] = handle["Unit"]
            self.fb.db.child("SensorsF").child(sensor_hash).set(sensor)

        return sensor_hash

    def setup_configs(self, plugin, sensor_key):
        global fb

        for config in plugin['Configs']:
            config_key = hashlib.md5()
            config_key.update(sensor_key)
            config_key.update(config["ChartKey"])
            for time_series in config['TimeSeries']:
                config_key.update(time_series["SeriesKey"])

            config_keyhash = config_key.hexdigest()
            config_result = self.fb.db.child("SensorConfigs").child(config_keyhash).get()
            if not config_result.val():
                self.logger.debug(
                    "Config {0} for plugin {1} does not exist on firebase. Creating with key {2}".format(
                        config["Name"], plugin[
                            'SensorName'], config_keyhash))
                config["SensorKey"] = sensor_key
                self.fb.db.child("SensorConfigs").child(config_keyhash).set(config)

            config_select_result = self.fb.db.child("SelectConfig").child(sensor_key).child(config["Name"]).child(
                config["ChartKey"]).get()
            if not config_select_result.val():
                self.fb.db.child("SelectConfig").child(sensor_key).child(config["Name"]).child(config["ChartKey"]).set(
                    config_keyhash)


if __name__ == "__main__":
    """The tagscanner runs in another thread, to continously check wether cards are scanned or not
    """
    instance = Gateway()

    DBusGMainLoop(set_as_default=True)
    gobject.threads_init()
    main_loop = gobject.MainLoop()
    bluetooth_thread = Thread(target=main_loop.run, args=())
    bluetooth_thread.daemon = True

    scanner_thread = threading.Thread(target=Last_tagged_user.main)
    scanner_thread.daemon = True
    scanner_thread.start()

    instance.logger.info("Loading all plugins from plugin directory.")
    sensors = instance.parse_plugins()

    if sensors is None:
        quit()

    if sensors is []:
        instance.logger.error("No plugins!")
        quit()

    instance.logger.info("Plugins loaded successfully")

    instance.logger.info("Subscribing to all sensors")

    assert isinstance(sensors, list)
    for sensor in sensors:
        assert isinstance(sensor, Sensor)
        sensor.subscribe()

    bluetooth_thread.start()
    instance.logger.info("Subscribed successfully.")
    x = None
    while not x == 'q':
        x = raw_input()

    instance.logger.info("Unsubscribing from all sensors")

    for sensor in sensors:
        sensor.unsubscribe()

    main_loop.quit()
    bluetooth_thread.join()