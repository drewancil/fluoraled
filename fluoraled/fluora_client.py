"""Send commands to a Fluora LED plant."""

import logging

from pythonosc.udp_client import SimpleUDPClient

from fluoraled.enums import AnimationMode, FluoraAnimations


class FluoraClient:
    """Fluora client."""

    def __init__(self, ip_address, udp_port) -> None:
        self.client_ip_address = ip_address
        self.client_udp_port = udp_port
        self.client = SimpleUDPClient(ip_address, udp_port)

    @property
    def effect_list(self) -> list[str]:
        """Return the list of supported effects."""
        return [effect.name.title() for effect in FluoraAnimations]

    def power(self, power_state: int):
        """Change the power state of the plant."""
        if power_state in (0, 1):
            logging.info("Plant command: Power %s", power_state)
            self.client.send_message("/SyYOTiXjQBjW", [power_state, power_state])
        else:
            raise ValueError("Power must be 0 (Off) or 1 (On)")

    def light_sensor(self, sensor_state: int):
        """Change the power state of the plant."""
        if sensor_state in (0, 1):
            logging.info("Plant command: Light sensor %s", sensor_state)
            self.client.send_message("/S53upLXAu7vg", [sensor_state, sensor_state])
        else:
            raise ValueError("Light Sensor must be 0 (Off) or 1 (On)")

    def reboot(self):
        """Reboot the plant."""
        logging.info("Plant command: Reboot")
        self.client.send_message("/pixelair/engine/reboot", [1, 0])

    def brightness_set(self, brightness_level: float):
        """Set the brightness level of the plant."""
        if brightness_level < 0.00 or brightness_level > 1.00:
            raise ValueError("Brightness must be between 0 and 1")
        logging.info("Plant command: Set Brightness %s", brightness_level)
        self.client.send_message("/Uv7aMFw5P2lX", [brightness_level, 0])

    def animation_set_mode(self, mode: str):
        """Set the animation mode."""
        if any(x for x in AnimationMode if x.name == mode):
            self.client.send_message("/iwaaMkVzOfUM", [AnimationMode[mode].value, 0])
        else:
            raise LookupError(f"Animation mode {mode} is unknown.")

    def animation_set(self, animat_name: str):
        """Set an animation."""
        if any(x for x in FluoraAnimations if x.name == animat_name.upper()):
            logging.info("Plant command: Set animation %s", animat_name)

            animation_num = int(FluoraAnimations[animat_name.upper()].value)
            # auto mode
            if animation_num == 0:
                self.animation_set_mode("AUTO")
            # manual mode animations
            if animation_num in range(100, 199):
                self.animation_set_mode("MANUAL")
                self.client.send_message("/tdU63ENxy4UG", [animation_num - 100, 0])
            # scene mode animations
            if animation_num in range(200, 299):
                self.animation_set_mode("SCENE")
                self.client.send_message("/EpUwZA1GSPjO", [animation_num - 200, 0])
        else:
            raise LookupError(f"Animation {animat_name} is unknown.")

    def audio_gain_set(self, audio_gain: float):
        """Set the audio gain level."""
        if audio_gain < 0.00 or audio_gain > 1.00:
            raise ValueError("Gain must be between 0 and 1")
        logging.info("Plant command: Set Audio Gain %s", audio_gain)
        self.client.send_message("/HwBeJeS0ufSp", [audio_gain, 0])

    def audio_attack_set(self, audio_attack: float):
        """Set the audio attack level."""
        if audio_attack < 0.00 or audio_attack > 1.00:
            raise ValueError("Attack must be between 0 and 1")
        logging.info("Plant command: Set Audio Attack %s", audio_attack)
        self.client.send_message("/HwBeGOxYN5Sp", [audio_attack, 0])

    def audio_release_set(self, audio_release: float):
        """Set the audio release level."""
        if audio_release < 0.00 or audio_release > 1.00:
            raise ValueError("Release must be between 0 and 1")
        logging.info("Plant command: Set Audio Release %s", audio_release)
        self.client.send_message("/HwBeogt1MBDp", [audio_release, 0])

    def audio_filter_set(self, audio_filter: float):
        """Set the audio filter level."""
        if audio_filter < 0.00 or audio_filter > 1.00:
            raise ValueError("Filter must be between 0 and 1")
        logging.info("Plant command: Set Audio Filter %s", audio_filter)
        self.client.send_message("/HwBeiitcOaSp", [audio_filter, 0])
