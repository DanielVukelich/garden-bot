from asyncio import Lock
import asyncio
from collections.abc import Awaitable
from datetime import datetime, timedelta
from typing import Any, Optional, Tuple

from src.relay import Solenoid, RelayController

class WateringJob():
    duration : timedelta
    solenoid : Solenoid
    actual_start : Optional[datetime] = None
    actual_end : Optional[datetime] = None

    def __init__(self, duration: timedelta, solenoid: Solenoid):
        self.duration = duration
        self.solenoid = solenoid

    def __repr__(self) -> str:
        return str(self.solenoid) + ' Duration: ' + str(self.duration) + 's Job start time: ' + str(self.actual_start) + ' Job end time: ' + str(self.actual_end)

class JobRunner():

    task : Optional[Awaitable[Any]]
    current_job : Optional[WateringJob] = None

    def __init__(self, solenoids: RelayController):
        self._relays = solenoids
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

    async def __run_job(self, job: WateringJob):
        assert (job.duration < timedelta(minutes=2.5)), 'job duration too long'
        assert (job.duration > timedelta(seconds=5)), 'job duration too short'

        print('Running job: ' + str(job))

        job.actual_start = datetime.utcnow()
        self._relays.solenoid_power_on(job.solenoid)
        self._relays.pump_power_on()
        try:
            await asyncio.sleep(job.duration.total_seconds())
        except Exception as e:
            print('Error running job: ' + str(job) + ' Exception: ' + str(e))
        finally:
            self._relays.everything_power_off()
            job.actual_end = datetime.utcnow()
        print('Done running job: ' + str(job))

        async with self._lock:
            self.current_job = None
            self.task = None
