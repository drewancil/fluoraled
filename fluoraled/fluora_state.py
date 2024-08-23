"""Floura Plant server for receiving state updates from plant."""

import json
import logging
import socketserver
import sys
from dataclasses import dataclass


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


@dataclass
class FluoraState:
    """Represents the state of a Fluora Plant."""

    model: str = ""
    rssi: int = 0
    mac_address: str = ""

    audio_filter: float = 0.0
    audio_release: float = 0.0
    audio_gain: float = 0.0
    audio_attack: float = 0.0

    light_sensor_enabled: bool = False

    brightness: float = 0.0
    main_light: bool = False

    animation_mode: int = 0
    active_animation: str = ""

    bloom: float = 0.0
    speed: float = 0.0
    size: float = 0.0


class FluoraServer(socketserver.UDPServer):
    """Starts UDP listener to receive state updates from the Fluora Plant.
    Sends state to MQTT for use in Home Assistant.
    """

    def __init__(self, server_address) -> None:
        logging.debug("fluora-server initializing")
        self.json_payload: str = ""
        self.packet_assemble = {}
        self.plant_state: dict = {}
        self.fluora_state = FluoraState()
        try:
            socketserver.UDPServer.__init__(self, server_address, FluoraUDPHandler)
        except OSError:
            logging.error("Server could not start as UDP address/port already in use")
            raise

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
        to plant_state after the final datagram in the series is received.
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
                rec_state = json.loads(self.json_payload)
                self.plant_state = rec_state
                self.update_state(rec_state)

                # logging.debug("plant_state: %s", self.plant_state)
                # self.plant_box = Box(self.plant_state)

            except json.JSONDecodeError as error:
                logging.error("JSON error: %s", error)
                return
            except TypeError as error:
                logging.error("JSON error: %s", error)
                return
        else:
            self.packet_assemble[udp_packet_seq] = udp_payload

        return socketserver.UDPServer.process_request(self, request, client_address)

    def update_state(self, rec_state) -> None:
        """Update the plant state."""
        self.fluora_state.model = rec_state["model"]
        self.fluora_state.rssi = rec_state["rssi"]
        self.fluora_state.mac_address = rec_state["network"]["macAddress"]
        self.fluora_state.audio_filter = rec_state["audio"]["filter"]["value"]
        self.fluora_state.audio_release = rec_state["audio"]["release"]["value"]
        self.fluora_state.audio_gain = rec_state["audio"]["gain"]["value"]
        self.fluora_state.audio_attack = rec_state["audio"]["attack"]["value"]
        self.fluora_state.light_sensor_enabled = rec_state["lightSensor"]["enabled"][
            "value"
        ]
        self.fluora_state.brightness = rec_state["engine"]["brightness"]["value"]
        self.fluora_state.main_light = rec_state["engine"]["isDisplaying"]["value"]
        self.fluora_state.animation_mode = rec_state["engine"]["manualMode"][
            "loadedAnimationIndex"
        ]
        self.fluora_state.active_animation = rec_state["engine"]["manualMode"][
            "activeAnimationIndex"
        ]["value"]
        self.fluora_state.bloom = rec_state["engine"]["manualMode"]["dashboard"][
            "Ve3ZS5tBUo4T"
        ]["value"]
        self.fluora_state.speed = rec_state["engine"]["manualMode"]["dashboard"][
            "Ve3ZSfv3PK4T"
        ]["value"]
        self.fluora_state.size = rec_state["engine"]["manualMode"]["dashboard"][
            "Ve3ZSfSgP54T"
        ]["value"]

    def server_close(self):
        """Complete me."""
        logging.debug("Stopping UDP server")
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
        self.fluora_server = FluoraServer(address)

    def _exit_handler(self, sig, frame):
        """Handles program exit via SIGINT from systemd or ctrl-c."""
        del sig, frame
        logging.info("Server: Shut down requested")
        self.fluora_server.server_close()
        sys.exit(0)
