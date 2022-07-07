from datetime import datetime, timedelta
from typing import Optional, Tuple
import threading
import gpiozero

class Frequency():
    hz: float
    count: int
    duration: timedelta

    def __init__(self, count: int, duration: timedelta):
        self.count = count
        self.duration = duration
        self.hz = count / duration.total_seconds()

class FlowRate():
    ONE_LITER_TO_GALLON = 0.2641729

    freq: Frequency
    magic_coefficient: int
    timestamp: datetime

    def __init__(self, monitor_freq: Frequency, magic_coefficient: int, timestamp: datetime):
        self.freq = monitor_freq
        self.coefficient = magic_coefficient
        self.timestamp = timestamp

    def gallons_per_min(self) -> float:
        return self.liters_per_min() * FlowRate.ONE_LITER_TO_GALLON

    def liters_per_min(self) -> float:
        return self.freq.hz / self.coefficient

class FlowMonitor():
    # 120Hz should be well beyond any measurement rate we expect from the cheap flow monitor used
    DEBOUNCE_SEC: float = 1/120
    SAMPLE_RATE: timedelta = timedelta(seconds=0.5)

    working_counter: int = 0
    last_measurment: Optional[Frequency] = None
    last_sampled: datetime = datetime.min
    lock: threading.Lock = threading.Lock()

    def __init__(self, flow_gpio: int, magic_flow_coefficient: int, max_sample_duration: timedelta):
        self.pin = gpiozero.DigitalInputDevice(flow_gpio, pull_up=False, bounce_time=FlowMonitor.DEBOUNCE_SEC)
        self.pin.when_activated = FlowMonitor.gpio_callback
        self.magic_coefficient = magic_flow_coefficient
        self.max_sample_duration = max_sample_duration

    def try_get_flow(self, last_measurement_since: datetime) -> Tuple[bool, Optional[FlowRate]]:
        if FlowMonitor.last_sampled < last_measurement_since or FlowMonitor.last_measurment is None:
            return (False, None)
        flow = FlowRate(FlowMonitor.last_measurment, self.magic_coefficient, FlowMonitor.last_sampled)

        # If we started to measure flow, then stopped the pump, then restarted the pump, we should reject the sample
        if flow.freq.duration > self.max_sample_duration:
            return (False, None)

        return (True, flow)

    @staticmethod
    def gpio_callback():
        # Generally you want to limit the amount of work done inside an interrupt handler.
        # Hopefully all this locking isn't too much for a pi to handle at 120Hz.
        try:
            FlowMonitor.lock.acquire()

            now = datetime.utcnow()
            sample_duration = now - FlowMonitor.last_sampled
            print(FlowMonitor.working_counter)
            if sample_duration < FlowMonitor.SAMPLE_RATE:
                FlowMonitor.working_counter += 1
                return

            FlowMonitor.last_sampled = now
            FlowMonitor.last_measurment = Frequency(FlowMonitor.working_counter, sample_duration)
            FlowMonitor.working_counter = 1
        finally:
            FlowMonitor.lock.release()
