"""."""

from enum import Enum


class AnimationMode(Enum):
    """Animation modes of the Fluora plant."""

    AUTO = 0
    SCENE = 1
    MANUAL = 2


class AnimationModeManual(Enum):
    """Animation names and number for manual mode."""

    LEAFSWIRL = 1
    SNAKES = 2
    STEMEQ = 3  # SR
    HUEEQ = 4  # SR
    BOOMCLAP = 5  # SR
    HUECYCLE = 6
    RAINBOW = 7
    RAINBOWBLOOM = 8
    TWINKLE = 9
    LEAFFADE = 10
    STEMFADE = 11
    SOLIDCOLOR = 12
    SWEEP = 13
    PULSE = 14


class AnimationsSoundReactive(Enum):
    """Sound reactive animations."""

    STEMEQ = 3
    HUEEQ = 4
    BOOMCLAP = 5


class AnimationModeAuto(Enum):
    """Animation names and number for auto mode."""

    TWINKLE = 0
    SNAKES = 1
    RAINBOWSWIRL = 2
    SWEEP = 3
    LEAFFADE = 4
    LEAFSWIRL = 5


class AnimationModeScene(Enum):
    """Animation names and number for scene mode."""

    PARTY = 0
    CHILL = 1
    FOCUS = 2
    BEDTIME = 3
    AWAKEN = 4


class FluoraAnimations(Enum):
    """Animation names for the Fluora LED plant
    0-99 - reserved for system - Auto mode
    100-199 - manual mode animations - subtract 100 to get the actual value
    200-299 - scene mode animations - subtract 200 to get the actual value
    """

    # system reserved
    AUTO = 0
    # manual mode animations
    LEAFSWIRL = 101
    SNAKES = 102
    STEMEQ = 103  # SR
    HUEEQ = 104  # SR
    BOOMCLAP = 105  # SR
    HUECYCLE = 106
    RAINBOW = 107
    RAINBOWBLOOM = 108
    TWINKLE = 109
    LEAFFADE = 110
    STEMFADE = 111
    SOLIDCOLOR = 112
    SWEEP = 113
    PULSE = 114
    # scene mode animations
    PARTY = 200
    CHILL = 201
    FOCUS = 202
    BEDTIME = 203
    AWAKEN = 204
