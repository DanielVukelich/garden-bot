from asyncio import AbstractEventLoop
import os
import asyncio
from datetime import timedelta
from quart import Quart, render_template, request
from gpiozero import Device
from gpiozero.pins.mock import MockFactory
from src.relay import SolenoidController, Solenoid, RelayId
from src.camera import WebCamHandler
from src.job_runner import JobRunner, WateringJob

async def index_handler():
    return await render_template("index.html")

class SolenoidHandler():

    def __init__(self, dispatcher: JobRunner):
        self.dispatcher = dispatcher

    async def get(self):
        id = request.args['id']
        solenoid = Solenoid[str(id)]
        (status, running_job) = await self.dispatcher.try_run_job(WateringJob(timedelta(seconds=6), solenoid))
        if not status:
            return 'The system is busy: ' + str(running_job)
        return 'Success: ' + str(running_job)

def init_hardware() -> SolenoidController:
    # For now, just mock the relays
    Device.pin_factory = MockFactory()

    # Define assign each relay a gpio pin on the RaspberryPi
    controller = SolenoidController({
        RelayId.Power: 14,
        RelayId.BankSelector: 15,
        RelayId.Bank0: 17,
        RelayId.Bank1: 27,
    })

    controller.initialize_relays()
    return controller

def startup(event_loop: AbstractEventLoop) -> Quart:
    app = Quart(__name__)

    controller = init_hardware()
    runner = JobRunner(controller)
    faucet_handler = SolenoidHandler(runner)
    camera = WebCamHandler(event_loop)

    app.add_url_rule('/', methods=['GET'], endpoint='index', view_func=index_handler)
    app.add_url_rule( '/api/runfaucet', endpoint='faucet', methods=['GET'], view_func=faucet_handler.get)
    app.add_url_rule('/camera', endpoint='camera', methods=['GET'], view_func=camera.get)

    return app

event_loop = asyncio.get_event_loop()
app = startup(event_loop)

if __name__ == "__main__":
    app.run(loop=event_loop)
