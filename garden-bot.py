from datetime import datetime, timedelta
from quart import Quart, Request, render_template, request
import json

from config import GardenBotConfig

from src.relay import Solenoid
from src.camera import WebCamHandler
from src.job_runner import WateringJob
from src.flow import FlowMonitor
from src.services import Services

class UiHandler():
    def __init__(self, services: Services):
        self.pins_mocked = services.config['USE_MOCK_PINS']

    async def get(self):
        return await render_template("index.html", solenoids=Solenoid, mocked_pins=self.pins_mocked)

class FlowRateHandler():

    def __init__(self, services: Services):
        self.allow_mocked_flow = services.config['USE_MOCK_PINS']
        self.flow_monitor = services.flow_monitor
        self.default_sample_age_cutoff = timedelta(seconds=5)

    async def post(self):
        # If we're running in a test env, allow a POST request to trigger the flow monitor's interrupt handler
        assert(self.allow_mocked_flow)
        FlowMonitor.gpio_callback()
        return "\"Ok\""

    async def get(self):
        try:
            date = request.args['from']
            sample_cutoff = datetime.fromisoformat(date)
        except Exception:
            sample_cutoff = datetime.utcnow() - self.default_sample_age_cutoff

        status, rate = self.flow_monitor.try_get_flow(sample_cutoff)
        response = {
            'L/min': 0.0,
            'G/min': 0.0,
            'timestamp': None
        }
        if status and rate is not None:
            response['L/min'] = rate.liters_per_min()
            response['G/min'] = rate.gallons_per_min()
            response['timestamp'] = rate.timestamp.isoformat()
        return response

class SolenoidHandler():

    def __init__(self, services: Services):
        self.dispatcher = services.job_runner

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
        volume = float(request.args['vol'])
        (status, running_job) = await self.dispatcher.try_run_job(WateringJob(volume, solenoid))
        response = {
            'queued': status,
            'current_job': running_job.to_dict(),
        }
        return json.dumps(response)

def startup() -> Quart:
    app = Quart(
        __name__,
        static_url_path='',
        static_folder='static/'
    )
    app.config.from_object(GardenBotConfig)

    services = Services(app.config)

    ui = UiHandler(services)
    flow_handler = FlowRateHandler(services)
    faucet_handler = SolenoidHandler(services)
    camera = WebCamHandler()

    app.add_url_rule('/', endpoint='get_index', methods=['GET'], view_func=ui.get)
    app.add_url_rule('/api/solenoid', endpoint='get_solenoid', methods=['GET'], view_func=faucet_handler.get)
    app.add_url_rule('/api/solenoid', endpoint='post_solenoid', methods=['POST'], view_func=faucet_handler.post)
    app.add_url_rule('/api/flow', endpoint='get_flow', methods=['GET'], view_func=flow_handler.get)
    app.add_url_rule('/api/flow', endpoint='post_flow', methods=['POST'], view_func=flow_handler.post)
    app.add_url_rule('/camera', endpoint='get_camera', methods=['GET'], view_func=camera.get)
    return app


app = startup()
if __name__ == "__main__":
    app.run()
