import socket
import time

ur_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
ur_socket.connect(("192.168.0.11", 30002))

def send_urscript(script):
    full_script = f"def test():\n  {script}\nend\n"
    ur_socket.send(full_script.encode())
    time.sleep(1)

# Test avec différentes syntaxes possibles
print("Test 1: rq_close()...")
send_urscript("rq_close()")
time.sleep(2)

print("Test 2: rq_open()...")
send_urscript("rq_open()")
time.sleep(2)

ur_socket.close()
print("Terminé")