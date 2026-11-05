import math
import socket
import struct


def osc_packet(pitch, yaw):
    if not all(math.isfinite(v) for v in (pitch, yaw)):
        raise ValueError("Eye angles must be finite")
    def string(value):
        raw = value.encode("ascii") + b"\0"
        return raw + b"\0" * (-len(raw) % 4)
    return string("/tracking/eye/CenterPitchYaw") + string(",ff") + struct.pack(">ff", pitch, yaw)


class EyeOutput:
    def __init__(self, port=9000):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.port = port
        self.sent = 0

    def send(self, angles):
        if not all(math.isfinite(float(v)) for v in angles):
            raise ValueError("Eye angles must be finite")
        pitch = max(-25., min(25., float(angles[0])))
        yaw = max(-35., min(35., float(angles[1])))
        self.socket.sendto(osc_packet(pitch, yaw), ("127.0.0.1", self.port))
        self.sent += 1

    def close(self):
        self.socket.close()
