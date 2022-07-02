Garden-Bot

Installation:

Setup virtualenv with make:
`make setup`

Install (setup assumes a device running RaspberryPi OS):
`make install` (requires root)

Otherwise:

Create a virtualenv
`python3 -m virtualenv venv`

Enter the virtualenv
`source venv/bin/activate`

Install requirements
`python3 -m pip install -r requirements.txt`

Run from within virtualenv
`hypercorn garden-bot:app` or `python3 garden-bot.py` for hot-reload debugging

Configuration:

If you're running this on a raspberry pi, make sure to set `USE_MOCK_PINS=False` in `config.py`.  Otherwise, the server will mock out the gpio pins and you won't actually control any relays.
