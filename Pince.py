import socket
import time

ur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ur_socket.connect(("192.168.0.11", 30002))


def send_urscript(script):
    ur_socket.send((script + "\n").encode())
    time.sleep(0.1)


# Script d'activation et contrôle du Hand-E via Modbus RTU
activate_script = '''
def gripper_prog():
  set_tool_voltage(24)
  set_tool_communication(True, 115200, 0, 1, 1.0, 3.5)
  sleep(0.5)

  # Activation du gripper (registre 0x03E8 = 1000)
  tool_modbus_write_byte(9, 0, 1)    # rACT = 1 (activer)
  sleep(1.5)

  # Fermer le gripper
  tool_modbus_write_byte(9, 0, 9)    # rACT=1, rGTO=1 (go to position)
  tool_modbus_write_byte(9, 3, 255)  # Position = 255 (fermé)
  tool_modbus_write_byte(9, 4, 255)  # Vitesse = 255
  tool_modbus_write_byte(9, 5, 255)  # Force = 255
  sleep(2)

  # Ouvrir le gripper
  tool_modbus_write_byte(9, 3, 0)    # Position = 0 (ouvert)
  sleep(2)
end
'''

print("Envoi du script gripper...")
ur_socket.send(activate_script.encode())
time.sleep(6)

ur_socket.close()
print("Terminé")