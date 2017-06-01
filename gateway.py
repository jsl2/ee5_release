"""Main gateway script to run on raspberry pi.
Monitors available sensor configurations and sends results to firebase.

Sensor modules are loaded at runtime depending on configuration.
All sensors must have a 'monitor' method, which when run will asynchronously to monitor
the sensor for measurements and send results to firebase.
"""
import gobject
import inspect
import logging
import os
from dbus.mainloop.glib import DBusGMainLoop
from importlib import import_module
import threading
import Last_tagged_user
import yaml

import firebase
from errors import PluginError
from sensor import Sensor


class Gateway(object):
    REQUIRED_PLUGIN_KEYS = {"SensorName", "ConnectionType", "Protocol", "Handles", "Configs"}

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

            # self.firebase_plugin_setup(plugin)

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


if __name__ == "__main__":
    """The tagscanner runs in another thread, to continously check wether cards are scanned or not
    """
    instance = Gateway()

    DBusGMainLoop(set_as_default=True)
    gobject.threads_init()
    main_loop = gobject.MainLoop()
    bluetooth_thread = threading.Thread(target=main_loop.run, args=())
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
