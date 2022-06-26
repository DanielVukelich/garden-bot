Garden-Bot

Installation:

Create a virtualenv
`python3 -m virtualenv venv`

Enter the virtualenv
`source venv/bin/activate`

Install requirements
`python3 -m pip install -r requirements.txt`

Run from within virtualenv
`hypercorn garden-bot:app`

If you're running this on a raspberry pi, make sure to set `USE_MOCK_PINS=False` in `config.py`.  Otherwise, the server will mock out the gpio pins and you won't actually control any relays.
