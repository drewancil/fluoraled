"""Floura Plant server for receiving state updates from plant."""

import json
import logging
import signal
import socketserver
import sys
import threading
import time
from pathlib import Path

import paho.mqtt.client as mqtt
from paho.mqtt.enums import CallbackAPIVersion
from paho.mqtt.packettypes import PacketTypes
from paho.mqtt.properties import Properties
from sagebrush.configuration import SagebrushConfig

from fluoraled.fluora_client import FluoraClient


class FluoraUDPHandler(socketserver.BaseRequestHandler):
    """
    UDP server handler.
    """

    def __init__(self, request, client_address, fl_server) -> None:
        socketserver.BaseRequestHandler.__init__(
            self, request, client_address, fl_server
        )

    def setup(self):
        return socketserver.BaseRequestHandler.setup(self)

    def finish(self):
        return socketserver.BaseRequestHandler.finish(self)

    def handle(self):
        data: bytearray = self.request[0].strip()
        logging.debug("Handle UDP: %s", data)


class FluoraServer(socketserver.UDPServer):
    """Starts UDP listener to receive state updates from the Fluora Plant.
    Sends state to MQTT for use in Home Assistant.
    """

    def __init__(self, server_address, handler_class=FluoraUDPHandler) -> None:
        app_path = Path(__file__)
        dir_abs = app_path.parent.absolute()
        self.config = SagebrushConfig(f"{dir_abs}/fluora2mqtt.yml")
        logging.info("#----- Fluora2MQTT Application Starting -----#")
        self.mqtt_client: mqtt.Client
        self.fluora_client = FluoraClient("192.168.4.48", 6767)
        self.json_payload: str = ""
        self.packet_assemble = {}
        self.plant_state: dict = {}
        try:
            socketserver.UDPServer.__init__(self, server_address, handler_class)
        except OSError:
            logging.error("Server could not start as UDP address/port already in use")
            raise

        self._mqtt_initialize()
        self._mqtt_connect()
        # threaded loop-leave main thread for blocking work / handles reconnect
        self.mqtt_client.loop_start()

    def _mqtt_initialize(self):
        """Initialize the MQTT Client"""
        mqtt_transport = "tcp"
        self.mqtt_client = mqtt.Client(
            CallbackAPIVersion.VERSION2,
            f"{self.config.client_name}",
            transport=mqtt_transport,
            protocol=mqtt.MQTTv5,
        )
        self.mqtt_client.on_connect = self._on_connect
        self.mqtt_client.on_disconnect = self._on_disconnect
        self.mqtt_client.on_message = self._on_message
        self.mqtt_client.username_pw_set(
            self.config.mqtt_user, self.config.mqtt_password
        )
        self.mqtt_client.will_set(
            f"{self.config.client_name}/status",
            payload="offline",
            qos=1,
            retain=True,
            properties=None,
        )

    def _mqtt_connect(self):
        """Connects to the MQTT broker and sets last will."""
        the_properties = Properties(PacketTypes.CONNECT)
        try:
            self.mqtt_client.connect(
                self.config.mqtt_server,
                self.config.mqtt_port,
                keepalive=60,
                clean_start=mqtt.MQTT_CLEAN_START_FIRST_ONLY,  # noqa: E501
                properties=the_properties,
            )
        except ConnectionError as error:
            logging.error("MQTT: Could not connect - error: %s", error)

    # pylint: disable=too-many-arguments
    def _on_connect(self, m_client, userdata, flags, reason_code, properties=None):
        """MQTT connect callback."""
        del m_client, userdata, flags, properties
        if reason_code == 0:
            logging.info("MQTT server connected successfully")
            self.mqtt_client.publish(
                f"{self.config.client_name}/status",
                payload="online",
                qos=1,
                retain=True,
                properties=None,
            )
            # resubscribe on disconnect/reconnect
            self.mqtt_client.subscribe(
                f"{self.config.client_name}/commands", options=None, properties=None
            )
            logging.info("MQTT: Subscribed to %s/commands", self.config.client_name)
        if reason_code > 0:
            logging.error("MQTT server connection failed with code: %s", reason_code)

    def _on_disconnect(self, m_client, userdata, flags, reason_code, properties=None):
        """MQTT disconnect callback."""
        del m_client, userdata, flags, properties
        if reason_code == 0:
            logging.debug("MQTT disconnected sucessfully")
        if reason_code > 0:
            logging.error(
                "MQTT server disconnected with code: %s - will auto-reconnect",
                reason_code,
            )

    def _mqtt_publish_message(self, msg_topic: str, msg_payload: str):
        state_topic = f"{self.config.client_name}/{msg_topic}"
        self.mqtt_client.publish(
            state_topic, msg_payload, qos=0, retain=True, properties=None
        )
        logging.info("MQTT published: %s", state_topic)

    def _on_message(self, m_client, userdata, msg):
        """Receive MQTT commands, decodes json,
        and sends for execution.
        """
        del m_client, userdata
        try:
            cmd_received = json.loads(msg.payload)
        except json.JSONDecodeError as error:
            logging.error("JSON error: %s", error)
            return
        except TypeError as error:
            logging.error("JSON error: %s", error)
            return
        logging.info(
            "Commands received - topic: %s | Payload: %s",
            msg.topic,
            json.dumps(cmd_received),
        )
        for entity, value in cmd_received.items():
            self._process_message(entity, value)

    def _process_message(self, entity, value):
        """Process the message into a plant command."""
        logging.info("Processing command: %s %s", entity, value)
        if entity == "plant_power":
            logging.info("Plant command: Power %s", value)
            try:
                self.fluora_client.power(int(value))
            except ValueError as error:
                logging.error("Value error: %s", error)

        if entity == "plant_reboot":
            logging.info("Plant command: Reboot")
            self.fluora_client.reboot()

        if entity == "plant_brightness":
            logging.info("Plant command: Brightness")
            try:
                self.fluora_client.brightness_set(float(value))
            except ValueError as error:
                logging.error("Value error: %s", error)

        if entity == "manual_animation":
            logging.info("Plant command: Manual Animation")
            try:
                self.fluora_client.animation_set_manual(value)
            except LookupError as error:
                logging.error("Lookup error: %s", error)

    def server_activate(self):
        """Complete me."""
        socketserver.UDPServer.server_activate(self)

    def serve_forever(self, poll_interval=0.5):
        """Complete me."""
        del poll_interval
        while True:
            self.handle_request()

    def handle_request(self):
        return socketserver.UDPServer.handle_request(self)

    def verify_request(self, request, client_address):
        """Complete me."""
        return socketserver.UDPServer.verify_request(self, request, client_address)

    def process_request(self, request, client_address):
        """Process incoming UDP datagrams from the plant.  A single state
        update is 12 datagrams, so they will be stored in memory and posted
        to MQTT after the final datagram in the series is received.
        """
        data = request[0]  # type: ignore
        # this bytes appears to be the UDP partial message number
        # data is bigger then 1024 byte packet
        udp_packet_seq = data[3]

        # strip bytes 0-3 to leave just json payload / decode to utf-8
        udp_payload_raw = data[4:]
        udp_payload = udp_payload_raw.decode("utf-8")

        # 1/12 udp datagrams with full plant light state (json)
        # clear the slate for a new json update
        if udp_packet_seq == 0:
            self.packet_assemble.clear()
            self.packet_assemble[0] = udp_payload
        if udp_packet_seq == 12:
            # this is the 12/12 (final) message - handle it here
            self.packet_assemble[12] = udp_payload
            msg_vals = self.packet_assemble.values()
            self.json_payload = "".join(msg_vals)
            logging.debug("json_payload: %s", self.json_payload)
            try:
                self.plant_state = json.loads(self.json_payload)
                logging.debug("plant_state: %s", self.plant_state)

                plant_payload = json.dumps(self.plant_state)
                self._mqtt_publish_message("plant_state", plant_payload)

            except json.JSONDecodeError as error:
                logging.error("JSON error: %s", error)
                return
            except TypeError as error:
                logging.error("JSON error: %s", error)
                return
        else:
            self.packet_assemble[udp_packet_seq] = udp_payload

        return socketserver.UDPServer.process_request(self, request, client_address)

    def server_close(self):
        """Complete me."""
        logging.info("FluoraServer: Shut down requested")
        logging.info("MQTT: Disconnecting from the server")
        self.mqtt_client.disconnect()
        time.sleep(3)
        self.mqtt_client.loop_stop()
        logging.info("MQTT: Loop stopped")
        logging.info("Stopping UDP server")
        return socketserver.UDPServer.server_close(self)

    def finish_request(self, request, client_address):
        """Complete me."""
        return socketserver.UDPServer.finish_request(self, request, client_address)

    def close_request_address(self, request_address):
        """Complete."""
        logging.debug("close_request(%s)", request_address)
        return socketserver.UDPServer.close_request(self, request_address)


class SagebrushControl:  # pylint: disable=too-few-public-methods
    """."""

    def __init__(self):
        address = ("192.168.4.156", 12345)
        self.fluora_server = FluoraServer(address, FluoraUDPHandler)

    def _exit_handler(self, sig, frame):
        """Handles program exit via SIGINT from systemd or ctrl-c."""
        del sig, frame
        logging.info("Server: Shut down requested")
        self.fluora_server.server_close()
        sys.exit(0)

    def main(self):
        """Main."""
        signal.signal(signal.SIGINT, self._exit_handler)  # type: ignore

        t = threading.Thread(target=self.fluora_server.serve_forever)
        # t.setDaemon(True)  # don't hang on exit
        t.start()
        ip, port = self.fluora_server.server_address
        logging.info("Fluora UDP server started (%s:%s)", ip, port)


if __name__ == "__main__":
    service = SagebrushControl()
    service.main()
