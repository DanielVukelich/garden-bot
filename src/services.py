from datetime import timedelta
from gpiozero import Device
from gpiozero.pins.mock import MockFactory
from gpiozero.pins.native import NativeFactory
from quart import Config

from src.flow import FlowMonitor
from src.job_runner import JobRunner
from src.relay import RelayController, RelayId

class Services:

    flow_monitor: FlowMonitor
    relay_controller: RelayController
    job_runner: JobRunner
    config: Config

    def __init__(self, config: Config):

        if config['USE_MOCK_PINS']:
            print('Using mocked GPIO pins')
            Device.pin_factory = MockFactory()
        else:
            print('Using raspi GPIO pins')
            Device.pin_factory = NativeFactory()

        # Define assign each relay a gpio pin on the RaspberryPi
        self.relay_controller = RelayController({
            RelayId.Power: 14,
            RelayId.BankSelector: 15,
            RelayId.Bank0: 27,
            RelayId.Bank1: 22,
        })

        self.relay_controller.initialize_relays()

        self.flow_monitor = FlowMonitor(
            flow_gpio=19,
            magic_flow_coefficient=config['FLOW_MAGIC_COEFFICIENT'],
            max_sample_duration=timedelta(seconds=10)
        )
        self.config = config
        self.job_runner = JobRunner(self.relay_controller, self.flow_monitor)
