
class GardenBotConfig():
    TEMPLATES_AUTO_RELOAD = True
    # Set to False when you're running on a raspberry pi.  True for when developing locally.
    USE_MOCK_PINS = True
    # The hall-effect flowmeter used takes frequency and divides it by this number to derive flow in L/min
    # Read the specs of your flowmeter to derive this value
    FLOW_MAGIC_COEFFICIENT = 42.0
