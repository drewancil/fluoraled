"""Floura Plant server for receiving state updates from plant."""

import json
import logging
import socketserver
import sys

from box import Box


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

    def __init__(self, server_address) -> None:
        logging.debug("fluora-server initializing")
        self.json_payload: str = ""
        self.packet_assemble = {}
        self.plant_state: dict = {}
        self.plant_box: Box = Box()
        try:
            socketserver.UDPServer.__init__(self, server_address, FluoraUDPHandler)
        except OSError:
            logging.error("Server could not start as UDP address/port already in use")
            raise

    @property
    def the_box(self) -> str | None:
        """Return the display name of this light."""
        if self.plant_box is None:
            return None
        return str(self.plant_box)

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
                self.plant_state = json.loads(self.json_payload)
                logging.debug("plant_state: %s", self.plant_state)
                self.plant_box = Box(self.plant_state)

                # plant_payload = json.dumps(self.plant_state)
                # logging.debug("plant_payload: %s", plant_payload)

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
