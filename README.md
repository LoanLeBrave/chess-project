# chess-project (test OCR)

Quick notes to run the test OCR script locally.

1) Create and activate the venv (already created in this repo as `.venv`):

```sh
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

2) Install system Tesseract (required by `pytesseract`):

Ubuntu/Debian:
```sh
sudo apt update
sudo apt install -y tesseract-ocr
```

Fedora:
```sh
sudo dnf install -y tesseract
```

Arch:
```sh
sudo pacman -S tesseract
```

3) Run the test (from project root or from `test/`):

```sh
source .venv/bin/activate
python3 test/test.py
```

If Tesseract is not installed the script will print a warning and skip OCR.
