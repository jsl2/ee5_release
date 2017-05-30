# ee5_release
On boot, following a git pull, the gateway will be started automatically

Python2.7 required.

To install other requirements:
sudo apt-get install build-essential bluez-utils libbluetooth-dev libdbus-glib-1-dev python-dbus
sudo pip install -r requirements.txt

To start the gateway manually:
sudo python gateway.py
Type 'q' followed by enter to exit

IMPORTANT:
-The key file for firebase authentication: ee5dashboard-firebase-adminsdk-v0ub6-acbcb82ad1.json, must be found in the parent directory.
-If the scanner is not plugged in, the gateway will not run