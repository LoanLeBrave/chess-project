#!/usr/bin/env python3
"""
UR Modbus Server (API >= 3.10)
------------------------------
- Uses pymodbus >= 3.10 (ModbusDeviceContext / devices=).
- Publishes Modbus-TCP on 0.0.0.0:502 (sudo required on macOS).
- Maps Input Registers (IR) 0..5 to X, Y, Z (mm) and RX, RY, RZ (deg*10).
- Maps Coil 0 to GO (set to 1 to trigger motion; the robot program should reset it to 0).
- Also listens on UDP 15100 to set these registers easily from the same Mac.

Install:
    pip install "pymodbus>=3.10,<4"

Robot (UR) mapping example (Installation → Modbus):
    Input Register 0 -> x_m
    Input Register 1 -> y_m
    Input Register 2 -> z_m
    Input Register 3 -> rx_deg10
    Input Register 4 -> ry_deg10
    Input Register 5 -> rz_deg10
    Coil 0           -> GO_coil

In your UR program, convert units then build pose_target:
    x_m_val  = x_m / 1000.0
    rx_rad   = (rx_deg10 / 10.0) * 3.14159 / 180.0
    pose_target = p[x_m_val, y_m_val, z_m_val, rx_rad, ry_rad, rz_rad]

Send a test pose from the same machine (UDP helper example):
    echo "300 0 400 0 0 0 1" | nc -u -w1 127.0.0.1 15100
or with the companion script send_pose.py (JSON over UDP).
"""

import json
import socket
import threading
from typing import Tuple

from pymodbus.datastore import (
    ModbusDeviceContext, ModbusServerContext, ModbusSequentialDataBlock
)
from pymodbus.server import StartTcpServer

MODBUS_HOST = "0.0.0.0"
MODBUS_PORT = 502
UDP_HOST    = "0.0.0.0"
UDP_PORT    = 15100

# Build the Modbus device/datastore
device = ModbusDeviceContext(
    di=ModbusSequentialDataBlock(0, [0] * 10),   # Discrete Inputs (unused)
    co=ModbusSequentialDataBlock(0, [0] * 10),   # Coils         : 0 = GO
    hr=ModbusSequentialDataBlock(0, [0] * 20),   # Holding Regs  (unused here)
    ir=ModbusSequentialDataBlock(0, [0] * 20),   # Input Regs    : 0..5 = X,Y,Z,RX,RY,RZ
)

# Server context (devices= for API >= 3.10)
context = ModbusServerContext(devices=device, single=True)

def _set_pose_and_go_mm_deg10(
    x_mm:int, y_mm:int, z_mm:int, rx_deg10:int, ry_deg10:int, rz_deg10:int, go:int=1
) -> None:
    """Write the 6 values into Input Registers 0..5 and set Coil 0 = GO."""
    vals = [x_mm, y_mm, z_mm, rx_deg10, ry_deg10, rz_deg10]
    # Clamp to 16-bit unsigned
    vals = [max(0, min(65535, int(v))) for v in vals]
    # 4 = Input Registers, 1 = Coils
    device.setValues(4, 0, vals)
    device.setValues(1, 0, [1 if go else 0])
    print(f"[Modbus] IR[0..5] = {vals}   Coil[0]= {1 if go else 0}")

def _parse_udp_payload(data: bytes) -> Tuple[int,int,int,int,int,int,int]:
    """
    Accept JSON: {"x":..,"y":..,"z":..,"rx":..,"ry":..,"rz":..,"go":0/1}
    Or space-separated: x y z rx ry rz [go]
    Units: mm for x,y,z; degrees for rx,ry,rz (converted to deg*10 here).
    """
    s = data.decode("utf-8").strip()
    if s.startswith("{"):
        obj = json.loads(s)
        x = int(round(float(obj["x"])))
        y = int(round(float(obj["y"])))
        z = int(round(float(obj["z"])))
        rx = int(round(float(obj["rx"]) * 10.0))  # deg -> deg*10
        ry = int(round(float(obj["ry"]) * 10.0))
        rz = int(round(float(obj["rz"]) * 10.0))
        go = int(obj.get("go", 1))
        return x, y, z, rx, ry, rz, go
    parts = s.split()
    if len(parts) < 6:
        raise ValueError("Need at least 6 values: x y z rx ry rz [go]")
    x, y, z = [int(round(float(v))) for v in parts[:3]]
    rx = int(round(float(parts[3]) * 10.0))
    ry = int(round(float(parts[4]) * 10.0))
    rz = int(round(float(parts[5]) * 10.0))
    go = int(parts[6]) if len(parts) >= 7 else 1
    return x, y, z, rx, ry, rz, go

def udp_listener() -> None:
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind((UDP_HOST, UDP_PORT))
    print(f"[UDP] Listening on {UDP_HOST}:{UDP_PORT}")
    while True:
        data, addr = sock.recvfrom(4096)
        try:
            x, y, z, rx, ry, rz, go = _parse_udp_payload(data)
            print(f"[UDP] From {addr}: x={x} y={y} z={z} rx={rx/10.0}° ry={ry/10.0}° rz={rz/10.0}° go={go}")
            _set_pose_and_go_mm_deg10(x, y, z, rx, ry, rz, go)
        except Exception as e:
            print(f"[UDP] Error parsing payload from {addr}: {e}")

def main() -> None:
    t = threading.Thread(target=udp_listener, daemon=True)
    t.start()
    print(f"[Modbus] Starting Modbus-TCP server on {MODBUS_HOST}:{MODBUS_PORT} (sudo likely required)")
    StartTcpServer(context, address=(MODBUS_HOST, MODBUS_PORT))

if __name__ == "__main__":
    main()
