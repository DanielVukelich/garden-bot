from asyncio import Lock
import asyncio
from collections.abc import Awaitable
from datetime import datetime, timedelta
from typing import Any, Dict, Optional, Tuple

from src.flow import FlowMonitor
from src.relay import Solenoid, RelayController

class WateringJob():
    solenoid : Solenoid
    target_volume: float
    actual_volume: float
    actual_start : Optional[datetime] = None
    actual_end : Optional[datetime] = None

    def __init__(self, volume_liters: float, solenoid: Solenoid):
        assert(volume_liters > 0)
        assert(volume_liters < 4)
        self.solenoid = solenoid
        self.target_volume = volume_liters
        self.actual_volume = 0

    def to_dict(self) -> Dict:
        return {
            'target_volume': self.target_volume,
            'actual_volume': self.actual_volume,
            'solenoid': self.solenoid.name,
            'job_started': self.actual_start.isoformat() if self.actual_start is not None else None,
            'job_ended': self.actual_end.isoformat() if self.actual_end is not None else None,
        }

class JobRunner():

    task : Optional[Awaitable[Any]]
    current_job : Optional[WateringJob] = None

    def __init__(self, solenoids: RelayController, flow_monitor: FlowMonitor):
        self._relays = solenoids
        self._flow_monitor = flow_monitor
        self._lock = Lock()
        self.task = None

    async def try_run_job(self, new_job: WateringJob) -> Tuple[bool, WateringJob]:
        if self.current_job != None:
            return (False, self.current_job)
        async with self._lock:
            if self.current_job != None:
                return (False, self.current_job)
            self.task = asyncio.create_task(self.__run_job(new_job))
            self.current_job = new_job
        return (True, self.current_job)

    def get_current_job(self) -> Optional[WateringJob]:
        return self.current_job

    async def __run_job(self, job: WateringJob):
        print('Running job: ' + str(job))

        job.actual_start = datetime.utcnow()
        self._relays.solenoid_power_on(job.solenoid)
        self._relays.pump_power_on()
        try:
            await self.__await_volume_flow(job)
        except Exception as e:
            print('Error running job: ' + str(job) + ' Exception: ' + str(e))
        finally:
            self._relays.everything_power_off()
            job.actual_end = datetime.utcnow()
        print('Done running job: ' + str(job))

        async with self._lock:
            self.current_job = None
            self.task = None

    async def __await_volume_flow(self, job: WateringJob):
        absolute_stop_watering = datetime.utcnow() + timedelta(minutes=2.5)
        last_sample_ts = datetime.utcnow()
        while datetime.utcnow() < absolute_stop_watering:
            await asyncio.sleep(0.5)
            status, flow =  self._flow_monitor.try_get_flow(last_sample_ts)
            if not status or flow is None:
                continue
            if flow.timestamp == last_sample_ts:
                continue
            sample_duration = flow.timestamp - last_sample_ts
            last_sample_ts = flow.timestamp
            liters = flow.liters_per_min() / sample_duration.total_seconds() / 60
            job.actual_volume += liters
            print('Watering job status: ' + str(job.actual_volume) + '/' + str(job.target_volume) + 'L')
            if job.actual_volume >= job.target_volume:
                print('Watering job reached target volume')
                return
        print('Watering job timed out')
