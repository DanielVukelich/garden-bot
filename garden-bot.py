from datetime import timedelta
from quart import Config, Quart, Request, render_template, request
from gpiozero import Device
from gpiozero.pins.native import NativeFactory
from gpiozero.pins.mock import MockFactory
import json

from src.relay import RelayController, Solenoid, RelayId
from src.camera import WebCamHandler
from src.job_runner import JobRunner, WateringJob
from config import GardenBotConfig

async def index_handler():
    return await render_template("index.html", solenoids=Solenoid)

class SolenoidHandler():

    def __init__(self, dispatcher: JobRunner):
        self.dispatcher = dispatcher

    @staticmethod
    def parse_solenoid(api_request: Request) -> Solenoid:
        id = api_request.args['id']
        return Solenoid[str(id)]

    async def get(self):
        job = self.dispatcher.get_current_job()
        response = {
            'status': 'idle' if job is None else 'busy',
            'current_job': None if job is None else job.to_dict(),
        }
        return json.dumps(response)

    async def post(self):
        solenoid = self.parse_solenoid(request)
        (status, running_job) = await self.dispatcher.try_run_job(WateringJob(timedelta(seconds=6), solenoid))
        response = {
            'queued': status,
            'current_job': running_job.to_dict(),
        }
        return json.dumps(response)

def init_hardware(config: Config) -> RelayController:
    if config['USE_MOCK_PINS']:
        print('Using mocked GPIO pins')
        Device.pin_factory = MockFactory()
    else:
        print('Using raspi GPIO pins')
        Device.pin_factory = NativeFactory()

    # Define assign each relay a gpio pin on the RaspberryPi
    controller = RelayController({
        RelayId.Power: 14,
        RelayId.BankSelector: 15,
        RelayId.Bank0: 27,
        RelayId.Bank1: 22,
    })

    controller.initialize_relays()
    return controller

def startup() -> Quart:
    app = Quart(__name__)
    app.config.from_object(GardenBotConfig)

    controller = init_hardware(app.config)
    runner = JobRunner(controller)
    faucet_handler = SolenoidHandler(runner)
    camera = WebCamHandler()

    app.add_url_rule('/', methods=['GET'], endpoint='index', view_func=index_handler)
    app.add_url_rule( '/api/solenoid', endpoint='get_solenoid', methods=['GET'], view_func=faucet_handler.get)
    app.add_url_rule( '/api/solenoid', endpoint='post_solenoid', methods=['POST'], view_func=faucet_handler.post)
    app.add_url_rule('/camera', endpoint='camera', methods=['GET'], view_func=camera.get)
    return app


app = startup()
if __name__ == "__main__":
    app.run()
