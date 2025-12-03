#!/usr/bin/env python3
"""
send_pose.py — small helper to send a pose to ur_modbus_server_api310.py via UDP
Usage:
    python3 send_pose.py --x 300 --y 0 --z 400 --rx 0 --ry 0 --rz 0 --host 127.0.0.1 --port 15100 [--no-go] [--gripper open|close|none]

Units:
- x,y,z are in millimeters (mm)
- rx,ry,rz are in degrees (°)
- by default, this sets go=1. Use --no-go to avoid setting it (rare).
- --gripper: control Robotiq Hand-E gripper (open/close/none)

You can also send raw JSON yourself if you prefer; this script just sends JSON.
"""
import argparse
import json
import socket

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--x", type=float, required=True)
    p.add_argument("--y", type=float, required=True)
    p.add_argument("--z", type=float, required=True)
    p.add_argument("--rx", type=float, required=True, help="degrees")
    p.add_argument("--ry", type=float, required=True, help="degrees")
    p.add_argument("--rz", type=float, required=True, help="degrees")
    p.add_argument("--host", type=str, default="127.0.0.1")
    p.add_argument("--port", type=int, default=15100)
    p.add_argument("--no-go", action="store_true", help="do not set go=1")
    p.add_argument("--gripper", type=str, choices=["open", "close", "none"], default="none",
                   help="Robotiq Hand-E gripper control: open, close, or none (default: none)")
    args = p.parse_args()

    # Gripper value: 1 = open, 0 = close, -1 = no change
    gripper_val = -1
    if args.gripper == "open":
        gripper_val = 1
    elif args.gripper == "close":
        gripper_val = 0

    payload = {
        "x": args.x, "y": args.y, "z": args.z,
        "rx": args.rx, "ry": args.ry, "rz": args.rz,
        "go": 0 if args.no_go else 1,
        "gripper": gripper_val
    }
    data = json.dumps(payload).encode("utf-8")
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.sendto(data, (args.host, args.port))
    print(f"Sent -> {args.host}:{args.port}  {payload}")

if __name__ == "__main__":
    main()
