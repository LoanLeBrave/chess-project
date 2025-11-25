import socket
import time

ur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ur_socket.connect(("192.168.0.11", 30002))

def send_urscript(script):
    ur_socket.send((script + "\n").encode())
    time.sleep(0.5)

# Activer la tension outil
send_urscript("set_tool_voltage(24)")
time.sleep(1)

# Test fermeture via Tool Digital Output
print("Test fermeture...")
send_urscript("set_tool_digital_out(0, True)")
time.sleep(2)

# Test ouverture
print("Test ouverture...")
send_urscript("set_tool_digital_out(0, False)")
time.sleep(2)

ur_socket.close()
print("Terminé")