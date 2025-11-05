import os
import shutil


class GoPro:
    def __init__(self):
        # pretend we're connected to a GoPro Wi-Fi
        self._mode = None

    def mode(self, *args, **kwargs):
        self._mode = args
        print("[goprocam stub] mode set to:", args)

    def shutter(self, value=True):
        # Simulate taking a photo by copying an existing image in the test dir
        test_dir = os.path.dirname(__file__)
        src = os.path.join(test_dir, "image_2.jpg")
        dst = os.path.join(test_dir, "photo_taken.jpg")
        try:
            shutil.copyfile(src, dst)
            print(f"[goprocam stub] shutter triggered, created {dst}")
            return True
        except FileNotFoundError:
            print("[goprocam stub] source image not found; shutter did nothing")
            return False

    def downloadLastMedia(self, filename):
        # copy the photo_taken.jpg to provided filename path
        test_dir = os.path.dirname(__file__)
        src = os.path.join(test_dir, "photo_taken.jpg")
        # if filename is relative, treat it as relative to caller cwd
        try:
            shutil.copyfile(src, filename)
            print(f"[goprocam stub] downloaded last media to {filename}")
            return True
        except FileNotFoundError:
            print("[goprocam stub] no media to download")
            return False
