from typing import Dict
import gpiozero
from enum import Enum

class Solenoid(Enum):
    S0 = 'Solenoid 0',
    S1 = 'Solenoid 1',
    S2 = 'Solenoid 2',
    S3 = 'Solenoid 3',

class RelayId(Enum):
    Power = 'Pump and Solenoid(s) Power Supply',
    BankSelector= 'Solenoid Bank Selector',
    Bank0 = 'Solenoid Bank 0',
    Bank1 = 'Solenoid Bank 1',

class CoilStatus(Enum):
    Off = 'Off',
    On = 'On',

class SolenoidController:

    def __init__(self, gpio_mapping: Dict[RelayId, int]):
        self.gpio_mapping = gpio_mapping
        self.solenoid_connections: dict[Solenoid, Dict[RelayId, CoilStatus]] = {}

        self.relays: dict[RelayId, Relay] = {}
        for relay_id, pin in gpio_mapping.items():
            self.relays[relay_id] = Relay(pin)

    def __connect_solenoid(self, solenoid_id: Solenoid, requires_relay_state: dict[RelayId, CoilStatus] ) -> None:
        assert (RelayId.Power not in requires_relay_state), 'A solenoid connection can not define the state of the power relay'
        self.solenoid_connections[solenoid_id] = requires_relay_state

    def initialize_relays(self) -> None:
        self.__connect_solenoid(Solenoid.S0, {
            RelayId.BankSelector: CoilStatus.Off,
            RelayId.Bank0: CoilStatus.Off,
            RelayId.Bank1: CoilStatus.Off
        })
        self.__connect_solenoid(Solenoid.S1, {
            RelayId.BankSelector: CoilStatus.Off,
            RelayId.Bank0: CoilStatus.On,
            RelayId.Bank1: CoilStatus.Off
        })
        self.__connect_solenoid(Solenoid.S2, {
             RelayId.BankSelector: CoilStatus.On,
             RelayId.Bank0: CoilStatus.Off,
             RelayId.Bank1: CoilStatus.Off
        })
        self.__connect_solenoid(Solenoid.S3, {
             RelayId.BankSelector: CoilStatus.On,
             RelayId.Bank0: CoilStatus.Off,
             RelayId.Bank1: CoilStatus.On
        })
        self.system_power_off()
        self.depower_all_solenoid_relays()


    def enable_solenoid(self, solenoid: Solenoid) -> None:
        desired_relay_state = self.solenoid_connections[solenoid]
        for relay_id, state in desired_relay_state.items():
            self.relays[relay_id].set(state)

    def depower_all_solenoid_relays(self) -> None:
        for relay_id in self.relays.keys():
            if relay_id != RelayId.Power:
                self.relays[relay_id].off()

    def system_power_on(self) -> None:
        self.relays[RelayId.Power].on()
        self.depower_all_solenoid_relays()

    def system_power_off(self) -> None:
        self.relays[RelayId.Power].off()
        self.depower_all_solenoid_relays()

class Relay:
    def __init__(self, gpio_pin: int):
        self.pin = gpio_pin
        self.relay = gpiozero.OutputDevice(gpio_pin, active_high=False, initial_value=False)
        self.status = CoilStatus.Off

    def set(self, status: CoilStatus):
        self.on() if status == CoilStatus.On else self.off()

    def on(self):
        self.relay.on()
        self.status = CoilStatus.On

    def off(self):
        self.relay.off()
        self.status = CoilStatus.Off
