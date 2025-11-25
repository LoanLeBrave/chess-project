from goprocam import GoProCamera, constants
import time

gopro = GoProCamera.GoPro()

print("Mode Photo…")
gopro.mode(constants.Mode.PhotoMode, constants.Mode.SubMode.Photo.Single)

time.sleep(1)

print("Déclenchement…")
gopro.shutter(constants.start)

time.sleep(2)

print("OK")
