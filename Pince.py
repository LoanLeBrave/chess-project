import socket
import time

ur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ur_socket.connect(("192.168.0.11", 30002))

script = """
def gripper_test():
  rq_activate_and_wait()
  sleep(0.5)
  rq_close_and_wait()
  sleep(1)
  rq_open_and_wait()
  sleep(1)
end
"""

print("Envoi du script...")
ur_socket.send(script.encode())
time.sleep(5)

ur_socket.close()
print("Terminé")