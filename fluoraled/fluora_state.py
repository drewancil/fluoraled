"""Floura Plant server for receiving state updates from plant."""

import json
import logging
import socketserver
import sys
from dataclasses import dataclass

from box import Box


class FluoraUDPHandler(socketserver.BaseRequestHandler):
    """UDP server handler."""

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
class FluoraState:  # pylint: disable=R0902
    """Represents the state of a Fluora Plant."""

    plant_box: Box = Box()

    model: str = ""
    rssi: int = 0
    mac_address: str = ""

    audio_filter: float = 0.0
    audio_release: float = 0.0
    audio_gain: float = 0.0
    audio_attack: float = 0.0

    light_sensor_enabled: bool = False

    main_light: bool = False
    brightness: float = 0.0

    animation_mode: int = 0
    active_animation: str = ""
    animation_bloom: float = 0.0
    animation_speed: float = 0.0
    animation_size: float = 0.0

    palette_saturation: float = 0.0
    palette_hue: float = 0.0


class FluoraServer(socketserver.UDPServer):
    """Starts UDP listener to receive state updates from the Fluora Plant.
    Sends state to MQTT for use in Home Assistant.
    """

    def __init__(self, server_address: str, port_number: int = 12345) -> None:
        """Initialize the UDP server to receive state updates from the plant.add()
        Plant will send updates to UDP:12345 by default.
        """
        logging.debug("fluora-server initializing")
        self._json_payload: str = ""
        self._packet_assemble = {}
        self.plant_state: dict = {}
        self.fluora_state = FluoraState()
        try:
            server_addr_port = (server_address, port_number)
            socketserver.UDPServer.__init__(self, server_addr_port, FluoraUDPHandler)
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

    def _handle_request(self):
        return socketserver.UDPServer.handle_request(self)

    def _verify_request(self, request, client_address):
        """Complete me."""
        return socketserver.UDPServer.verify_request(self, request, client_address)

    def _process_request(self, request, client_address):
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

        # series of 12 udp datagrams with full plant light state (json)
        if udp_packet_seq == 0:
            # clear the packet_assemble data for a new state update
            self._packet_assemble.clear()
            self._packet_assemble[0] = udp_payload
        if udp_packet_seq == 12:
            # final message in state update (12/12) - process state update
            self._packet_assemble[12] = udp_payload
            msg_vals = self._packet_assemble.values()
            self._json_payload = "".join(msg_vals)
            logging.debug("json_payload: %s", self._json_payload)
            try:
                state_update = json.loads(self._json_payload)
                self.plant_state = state_update
                self._update_state(state_update)

            except json.JSONDecodeError as error:
                logging.error("JSON error: %s", error)
                return
            except TypeError as error:
                logging.error("JSON error: %s", error)
                return
        else:
            # store the partial state update
            self._packet_assemble[udp_packet_seq] = udp_payload

        return socketserver.UDPServer.process_request(self, request, client_address)

    def _update_state(self, state_update) -> None:
        """Update the plant state dataclass."""
        # experiment with python-box for nested dict access
        plant_box = Box(state_update)
        logging.debug(plant_box)

        self.fluora_state.model = state_update["model"]
        self.fluora_state.rssi = state_update["rssi"]
        self.fluora_state.mac_address = state_update["network"]["macAddress"]
        self.fluora_state.audio_filter = state_update["audio"]["filter"]["value"]
        self.fluora_state.audio_release = state_update["audio"]["release"]["value"]
        self.fluora_state.audio_gain = state_update["audio"]["gain"]["value"]
        self.fluora_state.audio_attack = state_update["audio"]["attack"]["value"]
        self.fluora_state.light_sensor_enabled = state_update["lightSensor"]["enabled"][
            "value"
        ]
        self.fluora_state.brightness = state_update["engine"]["brightness"]["value"]
        self.fluora_state.main_light = state_update["engine"]["isDisplaying"]["value"]
        self.fluora_state.animation_mode = state_update["engine"]["manualMode"][
            "loadedAnimationIndex"
        ]
        self.fluora_state.active_animation = state_update["engine"]["manualMode"][
            "activeAnimationIndex"
        ]["value"]

        dashboard: dict = state_update["engine"]["manualMode"]["dashboard"]
        if "Ve3ZS5tBUo4T" in dashboard:
            self.fluora_state.animation_bloom = dashboard["Ve3ZS5tBUo4T"]["value"]
        if "Ve3ZSfv3PK4T" in dashboard:
            self.fluora_state.animation_speed = dashboard["Ve3ZSfv3PK4T"]["value"]
        if "Ve3ZSfSgP54T" in dashboard:
            self.fluora_state.animation_size = dashboard["Ve3ZSfSgP54T"]["value"]

        palette: dict = state_update["engine"]["manualMode"]["palette"]
        if "saturation" in palette:
            self.fluora_state.palette_saturation = palette["saturation"]["value"]
        if "hue" in palette:
            self.fluora_state.palette_hue = palette["hue"]["value"]

    def server_close(self):
        """Complete me."""
        logging.debug("Stopping UDP server")
        return socketserver.UDPServer.server_close(self)

    def _finish_request(self, request, client_address):
        """Complete me."""
        return socketserver.UDPServer.finish_request(self, request, client_address)

    def _close_request_address(self, request_address):
        """Complete."""
        logging.debug("close_request(%s)", request_address)
        return socketserver.UDPServer.close_request(self, request_address)


class SagebrushControl:  # pylint: disable=too-few-public-methods
    """."""

    def __init__(self):
        self.fluora_server = FluoraServer("192.168.4.156", 12345)

    def _exit_handler(self, sig, frame):
        """Handles program exit via SIGINT from systemd or ctrl-c."""
        del sig, frame
        logging.info("Server: Shut down requested")
        self.fluora_server.server_close()
        sys.exit(0)
