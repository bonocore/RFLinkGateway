import logging
import multiprocessing
import time

import paho.mqtt.client as mqtt

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        pass

    try:
        import unicodedata
        unicodedata.numeric(s)
        return True
    except (TypeError, ValueError):
        pass

    return False

class MQTTClient(multiprocessing.Process):
    def __init__(self, messageQ, commandQ, config):
        self.logger = logging.getLogger('RFLinkGW.MQTTClient')
        self.logger.info("Starting...")

        multiprocessing.Process.__init__(self)
        self.__messageQ = messageQ
        self.__commandQ = commandQ

        self.mqttDataPrefix = config['mqtt_prefix']
        self.mqttDataFormat = config['mqtt_format']
        self._mqttConn = mqtt.Client(client_id='RFLinkGateway')
        self._mqttConn.username_pw_set(username=config['mqtt_user'],password=config['mqtt_password'])
        self._mqttConn.reconnect_delay_set(min_delay=1, max_delay=5)

        self._mqttConn.on_connect = self._on_connect
        self._mqttConn.on_disconnect = self._on_disconnect
        self._mqttConn.on_publish = self._on_publish
        self._mqttConn.on_message = self._on_message
        self.logger.info("Before Connect Async")
        self._mqttConn.connect_async(config['mqtt_host'], port=config['mqtt_port'], keepalive=5)
        self.logger.info("After Connect Async")
        self.logger.info("Before Loop Forever")
        self._mqttConn.loop_forever(retry_first_connection=True)
        self.logger.info("After Loop Forever")

    def close(self):
        self.logger.info("Closing connection")
        self._mqttConn.disconnect()

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            self.logger.error("Unexpected disconnection.")
            self._mqttConn.reconnect()

    def _on_connect(self, client, userdata, flags, mid):
         self.logger.info("Connected ")

    def _on_publish(self, client, userdata, mid):
        self.logger.debug("Message " + str(mid) + " published.")

    def _on_message(self, client, userdata, message):
        self.logger.debug("Message received: %s" % (message))

        data = message.topic.replace(self.mqttDataPrefix + "/", "").split("/")
        data_out = {
            'method': 'subscribe',
            'topic': message.topic,
            'family': data[0],
            'deviceId': data[1],
            'param': data[3],
            'payload': message.payload.decode('ascii'),
            'qos': 1
        }
        self.__commandQ.put(data_out)

    def publish(self, task):
        topic = "%s/%s/%s/R/%s" % (self.mqttDataPrefix, task['family'], task['deviceId'], task['param'])

        if self.mqttDataFormat == 'json':
            if is_number(task['payload']):
                task['payload'] = '{"value": ' + str(task['payload']) + '}'
            else:
                task['payload'] = '{"value": "' + str(task['payload']) + '"}'

        try:
            self._mqttConn.publish(topic, payload=task['payload'])
            self.logger.debug('Sending:%s' % (task))
        except Exception as e:
            self.logger.error('Publish problem: %s' % (e))
            self.__messageQ.put(task)

    def run(self):
        self._mqttConn.subscribe("%s/+/+/W/+" % self.mqttDataPrefix)
        while True:
            if not self.__messageQ.empty():
                task = self.__messageQ.get()
                if task['method'] == 'publish':
                    self.publish(task)
            else:
                time.sleep(0.01)
