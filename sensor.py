class Sensor(object):
    def subscribe(self):
        raise NotImplementedError

    def unsubscribe(self):
        raise NotImplementedError
