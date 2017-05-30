"""Responsible for sending measurements to firebase

Example:
    firebase = new Firebase()
    firebase.send(measurements, user='r0482051', sensor='HBF-206IT')

Todo:
    * Firebase authentication
    * Check User / Sensor already exist in firebase before sending (validation)
"""

import hashlib
import os
import time
from threading import Lock

import pyrebase

import Last_tagged_user


class Firebase(object):
    def __init__(self):
        dir_path = os.path.dirname(os.path.realpath(__file__))
        service_account_path = os.path.join(dir_path, "../ee5dashboard-firebase-adminsdk-v0ub6-acbcb82ad1.json")
        config = {
            "apiKey": "",
            "authDomain": "",
            "databaseURL": "https://ee5dashboard.firebaseio.com/",
            "storageBucket": "",
            "serviceAccount": service_account_path
        }

        firebase = pyrebase.initialize_app(config)
        self.send_lock = Lock()
        self.db = firebase.database()

    def send(self, measurements, plugin=None, user='r0479950'):
        """Send set of measurements to firebase for a given user  and sensor.

        Args:
            measurements (dict): measurements in format
                {id: {'Value':'val', 'Time':'timestamp'}, id2: {'Value':val ... } ...}
            user (str): user identifier or unique name
            plugin (dict): plugin

        Returns:
            None
        """
        # Send can be called by multiple threads: get lock first
        self.send_lock.acquire()
        assert self.db
        if not user:
            user = Last_tagged_user.get_number()

        if not self.check_user(user):
            print("User", user, " doesn't exist")
            return
        # gateway.instance.setup_sensor(plugin)
        sensor_hash = hashlib.md5(plugin['SensorName']).hexdigest()
        firebase_measurements = self.db.child('MeasurementsF').child(user).child(sensor_hash).get().val()
        if firebase_measurements is None:
            firebase_measurements = {}
        for key, measurement in measurements.iteritems():
            try:
                assert isinstance(measurement, dict)
                assert 'Value' in measurement and 'Time' in measurement
                assert len(measurement) == 2
                series = 'S{0}'.format(key)
                if series not in firebase_measurements.keys():
                    firebase_measurements[series] = {}
                ts = str(int(time.time()) * 1000)
                firebase_measurements[series][ts] = measurement
                # series_path = sensor_path.child('S{0}'.format(key))
                # series_path.push(measurement)
            except AssertionError:
                print "Invalid measurement: {0}".format(measurement)

        self.db.child('MeasurementsF').child(user).child(sensor_hash).update(firebase_measurements)
        self.send_lock.release()

    def check_user(self, user=''):
        all_users = self.db.child('UsersF').get().val()
        if all_users is None:
            return False
        for user_check, values in all_users.iteritems():
            if user_check == user:
                return True
        return False
