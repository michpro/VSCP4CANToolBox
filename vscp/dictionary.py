# pylint: disable=line-too-long, missing-module-docstring, missing-class-docstring, missing-function-docstring

from functools import singledispatchmethod
from .utils import search

UNKNOWN_VALUE = 65534
UNKNOWN_NAME = "UNKNOWN"

class Dictionary:
    def __init__(self) -> None:
        pass


    def get(self) -> list:
        return _vscp_class_1_dict


    def priority_id(self, name: str) -> int:
        result = search(name, 'name', 'id', _vscp_priority)
        if not isinstance(result, int):
            result = _vscp_priority[-1]['id']
        return result


    def priority_name(self, var: int) -> str:
        result = search(var, 'id', 'name', _vscp_priority)
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def class_name(self, var: int) -> str:
        result = search(var, 'id', 'class', self.get())
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def class_id(self, name: str) -> int:
        result = search(name, 'class', 'id', self.get())
        if not isinstance(result, int):
            result = int(UNKNOWN_VALUE)
        return result


    def type_name(self, class_id: int, type_id: int) -> str:
        result = search(type_id, 'id', 'type', self.class_types(class_id))
        if not isinstance(result, str):
            result = str(UNKNOWN_NAME)
        return result


    def type_id(self, class_, type_: str) -> int:
        result = None
        if isinstance(class_, (int, str)):
            result = search(type_, 'type', 'id', self.class_types(class_))
        if not isinstance(result, int):
            result = int(UNKNOWN_VALUE)
        return result


    @singledispatchmethod
    def class_types(self, _var) -> list:
        return []


    @class_types.register
    def _(self, var: int) -> list:
        return search(var, 'id', 'types', self.get()) or []


    @class_types.register
    def _(self, var: str) -> list:
        return search(var, 'class', 'types', self.get()) or []


    def parse_data(self, class_id: int, type_id: int, data: list) -> list:
        data_descr = self._get_data_description(class_id, type_id)
        description = data_descr['str'] if 'str' in data_descr else ''
        result = [[description, '']]
        if 'dlc' in data_descr:
            idx = 0
            for itr in range(len(data_descr['dlc'])):
                data_len = data_descr['dlc'][itr]['l']
                data_type = data_descr['dlc'][itr]['t']
                data_str = data_descr['dlc'][itr]['d']
                value_str = self._convert(data_type, data[idx:(idx + data_len)])
                result.append([data_str, value_str])
                idx += data_len
        return result


    def _get_data_description(self, class_id: int, type_id: int) -> dict:
        result = search(type_id, 'id', 'descr', self.class_types(class_id))
        if not isinstance(result, dict):
            result = {}
        return result


    def _convert(self, data_type: str, data: list) -> str:
        match data_type:
            case 'int':
                try:
                    val = int.from_bytes(data, 'big', signed=True)
                except ValueError:
                    val = 0
                result = f'{val}'
            case 'uint':
                try:
                    val = int.from_bytes(data, 'big', signed=False)
                except ValueError:
                    val = 0
                result = f'{val}'
            case 'hexint':
                try:
                    val = int.from_bytes(data, 'big', signed=False)
                except ValueError:
                    val = 0
                width = 2 * len(data)
                result = f'0x{val:0{width}X}'
            case 'float':
                try:
                    val = memoryview(bytearray(data)).cast('d')[0]
                except ValueError:
                    val = 0.0
                result = f'{val:.7G}'
            case 'dtime1':
                try:
                    val = int.from_bytes(data, 'big') & 0x0000003FFFFFFFFF
                    year   = val >> 26 & 0x0FFF
                    month  = val >> 22 & 0x0F
                    day    = val >> 17 & 0x1F
                    hour   = val >> 12 & 0x1F
                    minute = val >> 6  & 0x3F
                    second = val >> 0  & 0x3F
                    result = f'{year:04d}-{month:02d}-{day:02d} {hour:02d}:{minute:02d}:{second:02d}'
                except ValueError:
                    result = '0000-00-00 00:00:00'
            case 'raw':
                result = ' '.join(f'0x{val:02X}' for val in data) if 0 != len(data) else ''
            case 'ascii':
                result = ''.join([chr(val) for val in data])
            case _:
                result = ''
        return result


_vscp_priority = [
    {'name': 'Highest',     'id': 0},
    {'name': 'Even higher', 'id': 1},
    {'name': 'Higher',      'id': 2},
    {'name': 'Normal high', 'id': 3},
    {'name': 'Normal low',  'id': 4},
    {'name': 'Lower',       'id': 5},
    {'name': 'Even lower',  'id': 6},
    {'name': 'Lowest',      'id': 7}
]
_class_1_protocol = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event.
    {'type': 'SEGCTRL_HEARTBEAT',                   'id': 1,    'descr': {}},  # Segment Controller Heartbeat.
    {'type': 'NEW_NODE_ONLINE',                     'id': 2,    'descr': {}},  # New node on line / Probe.
    {'type': 'PROBE_ACK',                           'id': 3,    'descr': {}},  # Probe ACK.
    {'type': 'RESERVED4',                           'id': 4,    'descr': {}},  # Reserved for future use.
    {'type': 'RESERVED5',                           'id': 5,    'descr': {}},  # Reserved for future use.
    {'type': 'SET_NICKNAME',                        'id': 6,    'descr': {}},  # Set nickname-ID for node.
    {'type': 'NICKNAME_ACCEPTED',                   'id': 7,    'descr': {}},  # Nickname-ID accepted.
    {'type': 'DROP_NICKNAME',                       'id': 8,    'descr': {}},  # Drop nickname-ID / Reset Device.
    {'type': 'READ_REGISTER',                       'id': 9,    'descr': {}},  # Read register.
    {'type': 'RW_RESPONSE',                         'id': 10,   'descr': {}},  # Read/Write response.
    {'type': 'WRITE_REGISTER',                      'id': 11,   'descr': {}},  # Write register.
    {'type': 'ENTER_BOOT_LOADER',                   'id': 12,   'descr': {}},  # Enter boot loader mode.
    {'type': 'ACK_BOOT_LOADER',                     'id': 13,   'descr': {}},  # ACK boot loader mode.
    {'type': 'NACK_BOOT_LOADER',                    'id': 14,   'descr': {}},  # NACK boot loader mode.
    {'type': 'START_BLOCK',                         'id': 15,   'descr': {}},  # Start block data transfer.
    {'type': 'BLOCK_DATA',                          'id': 16,   'descr': {}},  # Block data.
    {'type': 'BLOCK_DATA_ACK',                      'id': 17,   'descr': {}},  # ACK data block.
    {'type': 'BLOCK_DATA_NACK',                     'id': 18,   'descr': {}},  # NACK data block.
    {'type': 'PROGRAM_BLOCK_DATA',                  'id': 19,   'descr': {}},  # Program data block.
    {'type': 'PROGRAM_BLOCK_DATA_ACK',              'id': 20,   'descr': {}},  # ACK program data block.
    {'type': 'PROGRAM_BLOCK_DATA_NACK',             'id': 21,   'descr': {}},  # NACK program data block.
    {'type': 'ACTIVATE_NEW_IMAGE',                  'id': 22,   'descr': {}},  # Activate new image.
    {'type': 'RESET_DEVICE',                        'id': 23,   'descr': {}},  # GUID drop nickname-ID / reset device.
    {'type': 'PAGE_READ',                           'id': 24,   'descr': {}},  # Page read.
    {'type': 'PAGE_WRITE',                          'id': 25,   'descr': {}},  # Page write.
    {'type': 'RW_PAGE_RESPONSE',                    'id': 26,   'descr': {}},  # Read/Write page response.
    {'type': 'HIGH_END_SERVER_PROBE',               'id': 27,   'descr': {}},  # High end server/service probe.
    {'type': 'HIGH_END_SERVER_RESPONSE',            'id': 28,   'descr': {}},  # High end server/service response.
    {'type': 'INCREMENT_REGISTER',                  'id': 29,   'descr': {}},  # Increment register.
    {'type': 'DECREMENT_REGISTER',                  'id': 30,   'descr': {}},  # Decrement register.
    {'type': 'WHO_IS_THERE',                        'id': 31,   'descr': {'str': 'Who is there?',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Node-ID'}}
                                                                         }},   # Who is there?
    {'type': 'WHO_IS_THERE_RESPONSE',               'id': 32,   'descr': {'str': 'Who is there response',
                                                                          'dlc': {0: {'l': 1, 't': 'uint', 'd': 'Chunk index'},
                                                                                  1: {'l': 7, 't': 'raw', 'd': 'Chunk data'}}
                                                                         }},   # Who is there response.
    {'type': 'GET_MATRIX_INFO',                     'id': 33,   'descr': {}},  # Get decision matrix info.
    {'type': 'GET_MATRIX_INFO_RESPONSE',            'id': 34,   'descr': {}},  # Decision matrix info response.
    {'type': 'GET_EMBEDDED_MDF',                    'id': 35,   'descr': {}},  # Get embedded MDF.
    {'type': 'GET_EMBEDDED_MDF_RESPONSE',           'id': 36,   'descr': {}},  # Embedded MDF response.
    {'type': 'EXTENDED_PAGE_READ',                  'id': 37,   'descr': {}},  # Extended page read register.
    {'type': 'EXTENDED_PAGE_WRITE',                 'id': 38,   'descr': {}},  # Extended page write register.
    {'type': 'EXTENDED_PAGE_RESPONSE',              'id': 39,   'descr': {}},  # Extended page read/write response.
    {'type': 'GET_EVENT_INTEREST',                  'id': 40,   'descr': {}},  # Get event interest.
    {'type': 'GET_EVENT_INTEREST_RESPONSE',         'id': 41,   'descr': {}},  # Get event interest response.
    {'type': 'ACTIVATE_NEW_IMAGE_ACK',              'id': 48,   'descr': {}},  # Activate new image ACK.
    {'type': 'ACTIVATE_NEW_IMAGE_NACK',             'id': 49,   'descr': {}},  # Activate new image NACK.
    {'type': 'START_BLOCK_ACK',                     'id': 50,   'descr': {}},  # Block data transfer ACK.
    {'type': 'START_BLOCK_NACK',                    'id': 51,   'descr': {}},  # Block data transfer NACK.
    {'type': 'BLOCK_CHUNK_ACK',                     'id': 52,   'descr': {}},  # Block Data Chunk ACK.
    {'type': 'BLOCK_CHUNK_NACK',                    'id': 53,   'descr': {}},  # Block Data Chunk NACK.
    {'type': 'BOOT_LOADER_CHECK',                   'id': 54,   'descr': {}},  # Bootloader CHECK.
]
_class_1_alarm = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'WARNING',                             'id': 1,    'descr': {}},  # Warning
    {'type': 'ALARM',                               'id': 2,    'descr': {}},  # Alarm occurred
    {'type': 'SOUND',                               'id': 3,    'descr': {}},  # Alarm sound on/off
    {'type': 'LIGHT',                               'id': 4,    'descr': {}},  # Alarm light on/off
    {'type': 'POWER',                               'id': 5,    'descr': {}},  # Power on/off
    {'type': 'EMERGENCY_STOP',                      'id': 6,    'descr': {}},  # Emergency Stop
    {'type': 'EMERGENCY_PAUSE',                     'id': 7,    'descr': {}},  # Emergency Pause
    {'type': 'EMERGENCY_RESET',                     'id': 8,    'descr': {}},  # Emergency Reset
    {'type': 'EMERGENCY_RESUME',                    'id': 9,    'descr': {}},  # Emergency Resume
    {'type': 'ARM',                                 'id': 10,   'descr': {}},  # Arm
    {'type': 'DISARM',                              'id': 11,   'descr': {}},  # Disarm
    {'type': 'WATCHDOG',                            'id': 12,   'descr': {}},  # Watchdog
    {'type': 'RESET',                               'id': 13,   'descr': {}},  # Alarm reset
]
_class_1_security = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'MOTION',                              'id': 1,    'descr': {}},  # Motion Detect
    {'type': 'GLASS_BREAK',                         'id': 2,    'descr': {}},  # Glass break
    {'type': 'BEAM_BREAK',                          'id': 3,    'descr': {}},  # Beam break
    {'type': 'SENSOR_TAMPER',                       'id': 4,    'descr': {}},  # Sensor tamper
    {'type': 'SHOCK_SENSOR',                        'id': 5,    'descr': {}},  # Shock sensor
    {'type': 'SMOKE_SENSOR',                        'id': 6,    'descr': {}},  # Smoke sensor
    {'type': 'HEAT_SENSOR',                         'id': 7,    'descr': {}},  # Heat sensor
    {'type': 'PANIC_SWITCH',                        'id': 8,    'descr': {}},  # Panic switch
    {'type': 'DOOR_OPEN',                           'id': 9,    'descr': {}},  # Door Contact
    {'type': 'WINDOW_OPEN',                         'id': 10,   'descr': {}},  # Window Contact
    {'type': 'CO_SENSOR',                           'id': 11,   'descr': {}},  # CO Sensor
    {'type': 'FROST_DETECTED',                      'id': 12,   'descr': {}},  # Frost detected
    {'type': 'FLAME_DETECTED',                      'id': 13,   'descr': {}},  # Flame detected
    {'type': 'OXYGEN_LOW',                          'id': 14,   'descr': {}},  # Oxygen Low
    {'type': 'WEIGHT_DETECTED',                     'id': 15,   'descr': {}},  # Weight detected.
    {'type': 'WATER_DETECTED',                      'id': 16,   'descr': {}},  # Water detected.
    {'type': 'CONDENSATION_DETECTED',               'id': 17,   'descr': {}},  # Condensation detected.
    {'type': 'SOUND_DETECTED',                      'id': 18,   'descr': {}},  # Noise (sound) detected.
    {'type': 'HARMFUL_SOUND_LEVEL',                 'id': 19,   'descr': {}},  # Harmful sound levels detected.
    {'type': 'TAMPER',                              'id': 20,   'descr': {}},  # Tamper detected.
    {'type': 'AUTHENTICATED',                       'id': 21,   'descr': {}},  # Authenticated
    {'type': 'UNAUTHENTICATED',                     'id': 22,   'descr': {}},  # Unauthenticated
    {'type': 'AUTHORIZED',                          'id': 23,   'descr': {}},  # Authorized
    {'type': 'UNAUTHORIZED',                        'id': 24,   'descr': {}},  # Unauthorized
    {'type': 'ID_CHECK',                            'id': 25,   'descr': {}},  # ID check
    {'type': 'PIN_OK',                              'id': 26,   'descr': {}},  # Valid pin
    {'type': 'PIN_FAIL',                            'id': 27,   'descr': {}},  # Invalid pin
    {'type': 'PIN_WARNING',                         'id': 28,   'descr': {}},  # Pin warning
    {'type': 'PIN_ERROR',                           'id': 29,   'descr': {}},  # Pin error
    {'type': 'PASSWORD_OK',                         'id': 30,   'descr': {}},  # Valid password
    {'type': 'PASSWORD_FAIL',                       'id': 31,   'descr': {}},  # Invalid password
    {'type': 'PASSWORD_WARNING',                    'id': 32,   'descr': {}},  # Password warning
    {'type': 'PASSWORD_ERROR',                      'id': 33,   'descr': {}},  # Password error
    {'type': 'GAS_SENSOR',                          'id': 34,   'descr': {}},  # Gas
    {'type': 'IN_MOTION_DETECTED',                  'id': 35,   'descr': {}},  # In motion
    {'type': 'NOT_IN_MOTION_DETECTED',              'id': 36,   'descr': {}},  # Not in motion
    {'type': 'VIBRATION_DETECTED',                  'id': 37,   'descr': {}},  # Vibration
]
_class_1_measurement = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'COUNT',                               'id': 1,    'descr': {}},  # Count
    {'type': 'LENGTH',                              'id': 2,    'descr': {}},  # Length/Distance
    {'type': 'MASS',                                'id': 3,    'descr': {}},  # Mass
    {'type': 'TIME',                                'id': 4,    'descr': {}},  # Time
    {'type': 'ELECTRIC_CURRENT',                    'id': 5,    'descr': {}},  # Electric Current
    {'type': 'TEMPERATURE',                         'id': 6,    'descr': {}},  # Temperature
    {'type': 'AMOUNT_OF_SUBSTANCE',                 'id': 7,    'descr': {}},  # Amount of substance
    {'type': 'INTENSITY_OF_LIGHT',                  'id': 8,    'descr': {}},  # Luminous Intensity (Intensity of light)
    {'type': 'FREQUENCY',                           'id': 9,    'descr': {}},  # Frequency
    {'type': 'RADIOACTIVITY',                       'id': 10,   'descr': {}},  # Radioactivity and other random events
    {'type': 'FORCE',                               'id': 11,   'descr': {}},  # Force
    {'type': 'PRESSURE',                            'id': 12,   'descr': {}},  # Pressure
    {'type': 'ENERGY',                              'id': 13,   'descr': {}},  # Energy
    {'type': 'POWER',                               'id': 14,   'descr': {}},  # Power
    {'type': 'ELECTRICAL_CHARGE',                   'id': 15,   'descr': {}},  # Electrical Charge
    {'type': 'ELECTRICAL_POTENTIAL',                'id': 16,   'descr': {}},  # Electrical Potential (Voltage)
    {'type': 'ELECTRICAL_CAPACITANCE',              'id': 17,   'descr': {}},  # Electrical Capacitance
    {'type': 'ELECTRICAL_RESISTANCE',               'id': 18,   'descr': {}},  # Electrical Resistance
    {'type': 'ELECTRICAL_CONDUCTANCE',              'id': 19,   'descr': {}},  # Electrical Conductance
    {'type': 'MAGNETIC_FIELD_STRENGTH',             'id': 20,   'descr': {}},  # Magnetic Field Strength
    {'type': 'MAGNETIC_FLUX',                       'id': 21,   'descr': {}},  # Magnetic Flux
    {'type': 'MAGNETIC_FLUX_DENSITY',               'id': 22,   'descr': {}},  # Magnetic Flux Density
    {'type': 'INDUCTANCE',                          'id': 23,   'descr': {}},  # Inductance
    {'type': 'FLUX_OF_LIGHT',                       'id': 24,   'descr': {}},  # Luminous Flux
    {'type': 'ILLUMINANCE',                         'id': 25,   'descr': {}},  # Illuminance
    {'type': 'RADIATION_DOSE_ABSORBED',             'id': 26,   'descr': {}},  # Radiation dose (absorbed)
    {'type': 'CATALYTIC_ACITIVITY',                 'id': 27,   'descr': {}},  # Catalytic activity
    {'type': 'VOLUME',                              'id': 28,   'descr': {}},  # Volume
    {'type': 'SOUND_INTENSITY',                     'id': 29,   'descr': {}},  # Sound intensity
    {'type': 'ANGLE',                               'id': 30,   'descr': {}},  # Angle, direction or similar
    {'type': 'POSITION',                            'id': 31,   'descr': {}},  # Position WGS 84
    {'type': 'SPEED',                               'id': 32,   'descr': {}},  # Speed
    {'type': 'ACCELERATION',                        'id': 33,   'descr': {}},  # Acceleration
    {'type': 'TENSION',                             'id': 34,   'descr': {}},  # Tension
    {'type': 'HUMIDITY',                            'id': 35,   'descr': {}},  # Damp/moist (Hygrometer reading)
    {'type': 'FLOW',                                'id': 36,   'descr': {}},  # Flow
    {'type': 'THERMAL_RESISTANCE',                  'id': 37,   'descr': {}},  # Thermal resistance
    {'type': 'REFRACTIVE_POWER',                    'id': 38,   'descr': {}},  # Refractive (optical) power
    {'type': 'DYNAMIC_VISCOSITY',                   'id': 39,   'descr': {}},  # Dynamic viscosity
    {'type': 'SOUND_IMPEDANCE',                     'id': 40,   'descr': {}},  # Sound impedance
    {'type': 'SOUND_RESISTANCE',                    'id': 41,   'descr': {}},  # Sound resistance
    {'type': 'ELECTRIC_ELASTANCE',                  'id': 42,   'descr': {}},  # Electric elastance
    {'type': 'LUMINOUS_ENERGY',                     'id': 43,   'descr': {}},  # Luminous energy
    {'type': 'LUMINANCE',                           'id': 44,   'descr': {}},  # Luminance
    {'type': 'CHEMICAL_CONCENTRATION_MOLAR',        'id': 45,   'descr': {}},  # Chemical (molar) concentration
    {'type': 'CHEMICAL_CONCENTRATION_MASS',         'id': 46,   'descr': {}},  # Chemical (mass) concentration
    {'type': 'DOSE_EQVIVALENT',                     'id': 47,   'descr': {}},  # Reserved [TODO not reserved]
    {'type': 'RESERVED48',                          'id': 48,   'descr': {}},  # Reserved
    {'type': 'DEWPOINT',                            'id': 49,   'descr': {}},  # Dew Point
    {'type': 'RELATIVE_LEVEL',                      'id': 50,   'descr': {}},  # Relative Level
    {'type': 'ALTITUDE',                            'id': 51,   'descr': {}},  # Altitude
    {'type': 'AREA',                                'id': 52,   'descr': {}},  # Area
    {'type': 'RADIANT_INTENSITY',                   'id': 53,   'descr': {}},  # Radiant intensity
    {'type': 'RADIANCE',                            'id': 54,   'descr': {}},  # Radiance
    {'type': 'IRRADIANCE',                          'id': 55,   'descr': {}},  # Irradiance, Exitance, Radiosity
    {'type': 'SPECTRAL_RADIANCE',                   'id': 56,   'descr': {}},  # Spectral radiance
    {'type': 'SPECTRAL_IRRADIANCE',                 'id': 57,   'descr': {}},  # Spectral irradiance
    {'type': 'SOUND_PRESSURE',                      'id': 58,   'descr': {}},  # Sound pressure (acoustic pressure)
    {'type': 'SOUND_DENSITY',                       'id': 59,   'descr': {}},  # Sound energy density
    {'type': 'SOUND_LEVEL',                         'id': 60,   'descr': {}},  # Sound level
    {'type': 'RADIATION_DOSE_EQ',                   'id': 61,   'descr': {}},  # Radiation dose (equivalent)
    {'type': 'RADIATION_DOSE_EXPOSURE',             'id': 62,   'descr': {}},  # Radiation dose (exposure)
    {'type': 'POWER_FACTOR',                        'id': 63,   'descr': {}},  # Power factor
    {'type': 'REACTIVE_POWER',                      'id': 64,   'descr': {}},  # Reactive Power
    {'type': 'REACTIVE_ENERGY',                     'id': 65,   'descr': {}},  # Reactive Energy
]
_class_1_measurement_x1 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x2 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x3 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_measurement_x4 = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_data = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'IO',                                  'id': 1,    'descr': {}},  # I/O value
    {'type': 'AD',                                  'id': 2,    'descr': {}},  # A/D value
    {'type': 'DA',                                  'id': 3,    'descr': {}},  # D/A value
    {'type': 'RELATIVE_STRENGTH',                   'id': 4,    'descr': {}},  # Relative strength
    {'type': 'SIGNAL_LEVEL',                        'id': 5,    'descr': {}},  # Signal Level
    {'type': 'SIGNAL_QUALITY',                      'id': 6,    'descr': {}},  # Signal Quality
]
_class_1_information = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'BUTTON',                              'id': 1,    'descr': {}},  # Button
    {'type': 'MOUSE',                               'id': 2,    'descr': {}},  # Mouse
    {'type': 'ON',                                  'id': 3,    'descr': {}},  # On
    {'type': 'OFF',                                 'id': 4,    'descr': {}},  # Off
    {'type': 'ALIVE',                               'id': 5,    'descr': {}},  # Alive
    {'type': 'TERMINATING',                         'id': 6,    'descr': {}},  # Terminating
    {'type': 'OPENED',                              'id': 7,    'descr': {}},  # Opened
    {'type': 'CLOSED',                              'id': 8,    'descr': {}},  # Closed
    {'type': 'NODE_HEARTBEAT',                      'id': 9,    'descr': {'str': 'Node Heartbeat',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'User specified'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'}}
                                                                         }},  # Node Heartbeat
    {'type': 'BELOW_LIMIT',                         'id': 10,   'descr': {}},  # Below limit
    {'type': 'ABOVE_LIMIT',                         'id': 11,   'descr': {}},  # Above limit
    {'type': 'PULSE',                               'id': 12,   'descr': {}},  # Pulse
    {'type': 'ERROR',                               'id': 13,   'descr': {}},  # Error
    {'type': 'RESUMED',                             'id': 14,   'descr': {}},  # Resumed
    {'type': 'PAUSED',                              'id': 15,   'descr': {}},  # Paused
    {'type': 'SLEEP',                               'id': 16,   'descr': {}},  # Sleeping
    {'type': 'GOOD_MORNING',                        'id': 17,   'descr': {}},  # Good morning
    {'type': 'GOOD_DAY',                            'id': 18,   'descr': {}},  # Good day
    {'type': 'GOOD_AFTERNOON',                      'id': 19,   'descr': {}},  # Good afternoon
    {'type': 'GOOD_EVENING',                        'id': 20,   'descr': {}},  # Good evening
    {'type': 'GOOD_NIGHT',                          'id': 21,   'descr': {}},  # Good night
    {'type': 'SEE_YOU_SOON',                        'id': 22,   'descr': {}},  # See you soon
    {'type': 'GOODBYE',                             'id': 23,   'descr': {}},  # Goodbye
    {'type': 'STOP',                                'id': 24,   'descr': {}},  # Stop
    {'type': 'START',                               'id': 25,   'descr': {}},  # Start
    {'type': 'RESET_COMPLETED',                     'id': 26,   'descr': {}},  # ResetCompleted
    {'type': 'INTERRUPTED',                         'id': 27,   'descr': {}},  # Interrupted
    {'type': 'PREPARING_TO_SLEEP',                  'id': 28,   'descr': {}},  # PreparingToSleep
    {'type': 'WOKEN_UP',                            'id': 29,   'descr': {}},  # WokenUp
    {'type': 'DUSK',                                'id': 30,   'descr': {}},  # Dusk
    {'type': 'DAWN',                                'id': 31,   'descr': {}},  # Dawn
    {'type': 'ACTIVE',                              'id': 32,   'descr': {}},  # Active
    {'type': 'INACTIVE',                            'id': 33,   'descr': {}},  # Inactive
    {'type': 'BUSY',                                'id': 34,   'descr': {}},  # Busy
    {'type': 'IDLE',                                'id': 35,   'descr': {}},  # Idle
    {'type': 'STREAM_DATA',                         'id': 36,   'descr': {}},  # Stream Data
    {'type': 'TOKEN_ACTIVITY',                      'id': 37,   'descr': {}},  # Token Activity
    {'type': 'STREAM_DATA_WITH_ZONE',               'id': 38,   'descr': {}},  # Stream Data with zone
    {'type': 'CONFIRM',                             'id': 39,   'descr': {}},  # Confirm
    {'type': 'LEVEL_CHANGED',                       'id': 40,   'descr': {}},  # Level Changed
    {'type': 'WARNING',                             'id': 41,   'descr': {}},  # Warning
    {'type': 'STATE',                               'id': 42,   'descr': {}},  # State
    {'type': 'ACTION_TRIGGER',                      'id': 43,   'descr': {}},  # Action Trigger
    {'type': 'SUNRISE',                             'id': 44,   'descr': {}},  # Sunrise
    {'type': 'SUNSET',                              'id': 45,   'descr': {}},  # Sunset
    {'type': 'START_OF_RECORD',                     'id': 46,   'descr': {}},  # Start of record
    {'type': 'END_OF_RECORD',                       'id': 47,   'descr': {}},  # End of record
    {'type': 'PRESET_ACTIVE',                       'id': 48,   'descr': {}},  # Pre-set active
    {'type': 'DETECT',                              'id': 49,   'descr': {}},  # Detect
    {'type': 'OVERFLOW',                            'id': 50,   'descr': {}},  # Overflow
    {'type': 'BIG_LEVEL_CHANGED',                   'id': 51,   'descr': {}},  # Big level changed
    {'type': 'SUNRISE_TWILIGHT_START',              'id': 52,   'descr': {}},  # Civil sunrise twilight time
    {'type': 'SUNSET_TWILIGHT_START',               'id': 53,   'descr': {}},  # Civil sunset twilight time
    {'type': 'NAUTICAL_SUNRISE_TWILIGHT_START',     'id': 54,   'descr': {}},  # Nautical sunrise twilight time
    {'type': 'NAUTICAL_SUNSET_TWILIGHT_START',      'id': 55,   'descr': {}},  # Nautical sunset twilight time
    {'type': 'ASTRONOMICAL_SUNRISE_TWILIGHT_START', 'id': 56,   'descr': {}},  # Astronomical sunrise twilight time
    {'type': 'ASTRONOMICAL_SUNSET_TWILIGHT_START',  'id': 57,   'descr': {}},  # Astronomical sunset twilight time
    {'type': 'CALCULATED_NOON',                     'id': 58,   'descr': {}},  # Calculated Noon
    {'type': 'SHUTTER_UP',                          'id': 59,   'descr': {}},  # Shutter up
    {'type': 'SHUTTER_DOWN',                        'id': 60,   'descr': {}},  # Shutter down
    {'type': 'SHUTTER_LEFT',                        'id': 61,   'descr': {}},  # Shutter left
    {'type': 'SHUTTER_RIGHT',                       'id': 62,   'descr': {}},  # Shutter right
    {'type': 'SHUTTER_END_TOP',                     'id': 63,   'descr': {}},  # Shutter reached top end
    {'type': 'SHUTTER_END_BOTTOM',                  'id': 64,   'descr': {}},  # Shutter reached bottom end
    {'type': 'SHUTTER_END_MIDDLE',                  'id': 65,   'descr': {}},  # Shutter reached middle end
    {'type': 'SHUTTER_END_PRESET',                  'id': 66,   'descr': {}},  # Shutter reached preset end
    {'type': 'SHUTTER_END_LEFT',                    'id': 67,   'descr': {}},  # Shutter reached preset left
    {'type': 'SHUTTER_END_RIGHT',                   'id': 68,   'descr': {}},  # Shutter reached preset right
    {'type': 'LONG_CLICK',                          'id': 69,   'descr': {}},  # Long click
    {'type': 'SINGLE_CLICK',                        'id': 70,   'descr': {}},  # Single click
    {'type': 'DOUBLE_CLICK',                        'id': 71,   'descr': {}},  # Double click
    {'type': 'DATE',                                'id': 72,   'descr': {}},  # Date
    {'type': 'TIME',                                'id': 73,   'descr': {}},  # Time
    {'type': 'WEEKDAY',                             'id': 74,   'descr': {}},  # Weekday
    {'type': 'LOCK',                                'id': 75,   'descr': {}},  # Lock
    {'type': 'UNLOCK',                              'id': 76,   'descr': {}},  # Unlock
    {'type': 'DATETIME',                            'id': 77,   'descr': {'str': 'DateTime',
                                                                          'dlc': {0: {'l': 1, 't': 'hexint', 'd': 'Device index'},
                                                                                  1: {'l': 1, 't': 'hexint', 'd': 'Zone'},
                                                                                  2: {'l': 1, 't': 'hexint', 'd': 'SubZone'},
                                                                                  3: {'l': 5, 't': 'dtime1', 'd': 'Date/Time'}}
                                                                         }},   # DateTime
    {'type': 'RISING',                              'id': 78,   'descr': {}},  # Rising
    {'type': 'FALLING',                             'id': 79,   'descr': {}},  # Falling
    {'type': 'UPDATED',                             'id': 80,   'descr': {}},  # Updated
    {'type': 'CONNECT',                             'id': 81,   'descr': {}},  # Connect
    {'type': 'DISCONNECT',                          'id': 82,   'descr': {}},  # Disconnect
    {'type': 'RECONNECT',                           'id': 83,   'descr': {}},  # Reconnect
    {'type': 'ENTER',                               'id': 84,   'descr': {}},  # Enter
    {'type': 'EXIT',                                'id': 85,   'descr': {}},  # Exit
    {'type': 'INCREMENTED',                         'id': 86,   'descr': {}},  # Incremented
    {'type': 'DECREMENTED',                         'id': 87,   'descr': {}},  # Decremented
    {'type': 'PROXIMITY_DETECTED',                  'id': 88,   'descr': {}},  # Proximity detected
]
_class_1_control = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'MUTE',                                'id': 1,    'descr': {}},  # Mute on/off
    {'type': 'ALL_LAMPS',                           'id': 2,    'descr': {}},  # (All) Lamp(s) on/off
    {'type': 'OPEN',                                'id': 3,    'descr': {}},  # Open
    {'type': 'CLOSE',                               'id': 4,    'descr': {}},  # Close
    {'type': 'TURNON',                              'id': 5,    'descr': {}},  # TurnOn
    {'type': 'TURNOFF',                             'id': 6,    'descr': {}},  # TurnOff
    {'type': 'START',                               'id': 7,    'descr': {}},  # Start
    {'type': 'STOP',                                'id': 8,    'descr': {}},  # Stop
    {'type': 'RESET',                               'id': 9,    'descr': {}},  # Reset
    {'type': 'INTERRUPT',                           'id': 10,   'descr': {}},  # Interrupt
    {'type': 'SLEEP',                               'id': 11,   'descr': {}},  # Sleep
    {'type': 'WAKEUP',                              'id': 12,   'descr': {}},  # Wakeup
    {'type': 'RESUME',                              'id': 13,   'descr': {}},  # Resume
    {'type': 'PAUSE',                               'id': 14,   'descr': {}},  # Pause
    {'type': 'ACTIVATE',                            'id': 15,   'descr': {}},  # Activate
    {'type': 'DEACTIVATE',                          'id': 16,   'descr': {}},  # Deactivate
    {'type': 'RESERVED17',                          'id': 17,   'descr': {}},  # Reserved for future use
    {'type': 'RESERVED18',                          'id': 18,   'descr': {}},  # Reserved for future use
    {'type': 'RESERVED19',                          'id': 19,   'descr': {}},  # Reserved for future use
    {'type': 'DIM_LAMPS',                           'id': 20,   'descr': {}},  # Dim lamp(s)
    {'type': 'CHANGE_CHANNEL',                      'id': 21,   'descr': {}},  # Change Channel
    {'type': 'CHANGE_LEVEL',                        'id': 22,   'descr': {}},  # Change Level
    {'type': 'RELATIVE_CHANGE_LEVEL',               'id': 23,   'descr': {}},  # Relative Change Level
    {'type': 'MEASUREMENT_REQUEST',                 'id': 24,   'descr': {}},  # Measurement Request
    {'type': 'STREAM_DATA',                         'id': 25,   'descr': {}},  # Stream Data
    {'type': 'SYNC',                                'id': 26,   'descr': {}},  # Sync
    {'type': 'ZONED_STREAM_DATA',                   'id': 27,   'descr': {}},  # Zoned Stream Data
    {'type': 'SET_PRESET',                          'id': 28,   'descr': {}},  # Set Pre-set
    {'type': 'TOGGLE_STATE',                        'id': 29,   'descr': {}},  # Toggle state
    {'type': 'TIMED_PULSE_ON',                      'id': 30,   'descr': {}},  # Timed pulse on
    {'type': 'TIMED_PULSE_OFF',                     'id': 31,   'descr': {}},  # Timed pulse off
    {'type': 'SET_COUNTRY_LANGUAGE',                'id': 32,   'descr': {}},  # Set country/language
    {'type': 'BIG_CHANGE_LEVEL',                    'id': 33,   'descr': {}},  # Big Change level
    {'type': 'SHUTTER_UP',                          'id': 34,   'descr': {}},  # Move shutter up
    {'type': 'SHUTTER_DOWN',                        'id': 35,   'descr': {}},  # Move shutter down
    {'type': 'SHUTTER_LEFT',                        'id': 36,   'descr': {}},  # Move shutter left
    {'type': 'SHUTTER_RIGHT',                       'id': 37,   'descr': {}},  # Move shutter right
    {'type': 'SHUTTER_MIDDLE',                      'id': 38,   'descr': {}},  # Move shutter to middle position
    {'type': 'SHUTTER_PRESET',                      'id': 39,   'descr': {}},  # Move shutter to preset position
    {'type': 'ALL_LAMPS_ON',                        'id': 40,   'descr': {}},  # (All) Lamp(s) on
    {'type': 'ALL_LAMPS_OFF',                       'id': 41,   'descr': {}},  # (All) Lamp(s) off
    {'type': 'LOCK',                                'id': 42,   'descr': {}},  # Lock
    {'type': 'UNLOCK',                              'id': 43,   'descr': {}},  # Unlock
    {'type': 'PWM',                                 'id': 44,   'descr': {}},  # PWM set
    {'type': 'TOKEN_LOCK',                          'id': 45,   'descr': {}},  # Lock with token
    {'type': 'TOKEN_UNLOCK',                        'id': 46,   'descr': {}},  # Unlock with token
    {'type': 'SET_SECURITY_LEVEL',                  'id': 47,   'descr': {}},  # Set security level
    {'type': 'SET_SECURITY_PIN',                    'id': 48,   'descr': {}},  # Set security pin
    {'type': 'SET_SECURITY_PASSWORD',               'id': 49,   'descr': {}},  # Set security password
    {'type': 'SET_SECURITY_TOKEN',                  'id': 50,   'descr': {}},  # Set security token
    {'type': 'REQUEST_SECURITY_TOKEN',              'id': 51,   'descr': {}},  # Request new security token
    {'type': 'INCREMENT',                           'id': 52,   'descr': {}},  # Increment
    {'type': 'DECREMENT',                           'id': 53,   'descr': {}},  # Decrement
]
_class_1_multimedia = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'PLAYBACK',                            'id': 1,    'descr': {}},  # Playback
    {'type': 'NAVIGATOR_KEY_ENG',                   'id': 2,    'descr': {}},  # NavigatorKey English
    {'type': 'ADJUST_CONTRAST',                     'id': 3,    'descr': {}},  # Adjust Contrast
    {'type': 'ADJUST_FOCUS',                        'id': 4,    'descr': {}},  # Adjust Focus
    {'type': 'ADJUST_TINT',                         'id': 5,    'descr': {}},  # Adjust Tint
    {'type': 'ADJUST_COLOUR_BALANCE',               'id': 6,    'descr': {}},  # Adjust Color Balance
    {'type': 'ADJUST_BRIGHTNESS',                   'id': 7,    'descr': {}},  # Adjust Brightness
    {'type': 'ADJUST_HUE',                          'id': 8,    'descr': {}},  # Adjust Hue
    {'type': 'ADJUST_BASS',                         'id': 9,    'descr': {}},  # Adjust Bass
    {'type': 'ADJUST_TREBLE',                       'id': 10,   'descr': {}},  # Adjust Treble
    {'type': 'ADJUST_MASTER_VOLUME',                'id': 11,   'descr': {}},  # Adjust Master Volume
    {'type': 'ADJUST_FRONT_VOLUME',                 'id': 12,   'descr': {}},  # Adjust Front Volume
    {'type': 'ADJUST_CENTRE_VOLUME',                'id': 13,   'descr': {}},  # Adjust Center Volume
    {'type': 'ADJUST_REAR_VOLUME',                  'id': 14,   'descr': {}},  # Adjust Rear Volume
    {'type': 'ADJUST_SIDE_VOLUME',                  'id': 15,   'descr': {}},  # Adjust Side Volume
    {'type': 'RESERVED16',                          'id': 16,   'descr': {}},  # Reserved
    {'type': 'RESERVED17',                          'id': 17,   'descr': {}},  # Reserved
    {'type': 'RESERVED18',                          'id': 18,   'descr': {}},  # Reserved
    {'type': 'RESERVED19',                          'id': 19,   'descr': {}},  # Reserved
    {'type': 'ADJUST_SELECT_DISK',                  'id': 20,   'descr': {}},  # Select Disk
    {'type': 'ADJUST_SELECT_TRACK',                 'id': 21,   'descr': {}},  # Select Track
    {'type': 'ADJUST_SELECT_ALBUM',                 'id': 22,   'descr': {}},  # Select Album/Play list
    {'type': 'ADJUST_SELECT_CHANNEL',               'id': 23,   'descr': {}},  # Select Channel
    {'type': 'ADJUST_SELECT_PAGE',                  'id': 24,   'descr': {}},  # Select Page
    {'type': 'ADJUST_SELECT_CHAPTER',               'id': 25,   'descr': {}},  # Select Chapter
    {'type': 'ADJUST_SELECT_SCREEN_FORMAT',         'id': 26,   'descr': {}},  # Select Screen Format
    {'type': 'ADJUST_SELECT_INPUT_SOURCE',          'id': 27,   'descr': {}},  # Select Input Source
    {'type': 'ADJUST_SELECT_OUTPUT',                'id': 28,   'descr': {}},  # Select Output
    {'type': 'RECORD',                              'id': 29,   'descr': {}},  # Record
    {'type': 'SET_RECORDING_VOLUME',                'id': 30,   'descr': {}},  # Set Recording Volume
    {'type': 'TIVO_FUNCTION',                       'id': 40,   'descr': {}},  # Tivo Function
    {'type': 'GET_CURRENT_TITLE',                   'id': 50,   'descr': {}},  # Get Current Title
    {'type': 'SET_POSITION',                        'id': 51,   'descr': {}},  # Set media position in milliseconds
    {'type': 'GET_MEDIA_INFO',                      'id': 52,   'descr': {}},  # Get media information
    {'type': 'REMOVE_ITEM',                         'id': 53,   'descr': {}},  # Remove Item from Album
    {'type': 'REMOVE_ALL_ITEMS',                    'id': 54,   'descr': {}},  # Remove all Items from Album
    {'type': 'SAVE_ALBUM',                          'id': 55,   'descr': {}},  # Save Album/Play list
    {'type': 'CONTROL',                             'id': 60,   'descr': {}},  # Multimedia Control
    {'type': 'CONTROL_RESPONSE',                    'id': 61,   'descr': {}},  # Multimedia Control response
]
_class_1_aol = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'UNPLUGGED_POWER',                     'id': 1,    'descr': {}},  # System unplugged from power source
    {'type': 'UNPLUGGED_LAN',                       'id': 2,    'descr': {}},  # System unplugged from network
    {'type': 'CHASSIS_INTRUSION',                   'id': 3,    'descr': {}},  # Chassis intrusion
    {'type': 'PROCESSOR_REMOVAL',                   'id': 4,    'descr': {}},  # Processor removal
    {'type': 'ENVIRONMENT_ERROR',                   'id': 5,    'descr': {}},  # System environmental errors
    {'type': 'HIGH_TEMPERATURE',                    'id': 6,    'descr': {}},  # High temperature
    {'type': 'FAN_SPEED',                           'id': 7,    'descr': {}},  # Fan speed problem
    {'type': 'VOLTAGE_FLUCTUATIONS',                'id': 8,    'descr': {}},  # Voltage fluctuations
    {'type': 'OS_ERROR',                            'id': 9,    'descr': {}},  # Operating system errors
    {'type': 'POWER_ON_ERROR',                      'id': 10,   'descr': {}},  # System power-on error
    {'type': 'SYSTEM_HUNG',                         'id': 11,   'descr': {}},  # System is hung
    {'type': 'COMPONENT_FAILURE',                   'id': 12,   'descr': {}},  # Component failure
    {'type': 'REBOOT_UPON_FAILURE',                 'id': 13,   'descr': {}},  # Remote system reboot upon report of a critical failure
    {'type': 'REPAIR_OPERATING_SYSTEM',             'id': 14,   'descr': {}},  # Repair Operating System
    {'type': 'UPDATE_BIOS_IMAGE',                   'id': 15,   'descr': {}},  # Update BIOS image
    {'type': 'UPDATE_DIAGNOSTIC_PROCEDURE',         'id': 16,   'descr': {}},  # Update Perform other diagnostic procedures
]
_class_1_measurement_64 = _class_1_measurement
_class_1_measurement_64_x1 = _class_1_measurement_x1
_class_1_measurement_64_x2 = _class_1_measurement_x2
_class_1_measurement_64_x3 = _class_1_measurement_x3
_class_1_measurement_64_x4 = _class_1_measurement_x4
_class_1_measure_zone = _class_1_measurement
_class_1_measure_zone_x1 = _class_1_measurement_x1
_class_1_measure_zone_x2 = _class_1_measurement_x2
_class_1_measure_zone_x3 = _class_1_measurement_x3
_class_1_measure_zone_x4 = _class_1_measurement_x4
_class_1_measurement_32 = _class_1_measurement
_class_1_measurement_32_x1 = _class_1_measurement_x1
_class_1_measurement_32_x2 = _class_1_measurement_x2
_class_1_measurement_32_x3 = _class_1_measurement_x3
_class_1_measurement_32_x4 = _class_1_measurement_x4
_class_1_set_value_zone = _class_1_measurement
_class_1_set_value_zone_x1 = _class_1_measurement_x1
_class_1_set_value_zone_x2 = _class_1_measurement_x2
_class_1_set_value_zone_x3 = _class_1_measurement_x3
_class_1_set_value_zone_x4 = _class_1_measurement_x4
_class_1_weather = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'SEASONS_WINTER',                      'id': 1,    'descr': {}},  # Season winter
    {'type': 'SEASONS_SPRING',                      'id': 2,    'descr': {}},  # Season spring
    {'type': 'SEASONS_SUMMER',                      'id': 3,    'descr': {}},  # Season summer
    {'type': 'SEASONS_AUTUMN',                      'id': 4,    'descr': {}},  # Autumn summer
    {'type': 'WIND_NONE',                           'id': 5,    'descr': {}},  # No wind
    {'type': 'WIND_LOW',                            'id': 6,    'descr': {}},  # Low wind
    {'type': 'WIND_MEDIUM',                         'id': 7,    'descr': {}},  # Medium wind
    {'type': 'WIND_HIGH',                           'id': 8,    'descr': {}},  # High wind
    {'type': 'WIND_VERY_HIGH',                      'id': 9,    'descr': {}},  # Very high wind
    {'type': 'AIR_FOGGY',                           'id': 10,   'descr': {}},  # Air foggy
    {'type': 'AIR_FREEZING',                        'id': 11,   'descr': {}},  # Air freezing
    {'type': 'AIR_VERY_COLD',                       'id': 12,   'descr': {}},  # Air Very cold
    {'type': 'AIR_COLD',                            'id': 13,   'descr': {}},  # Air cold
    {'type': 'AIR_NORMAL',                          'id': 14,   'descr': {}},  # Air normal
    {'type': 'AIR_HOT',                             'id': 15,   'descr': {}},  # Air hot
    {'type': 'AIR_VERY_HOT',                        'id': 16,   'descr': {}},  # Air very hot
    {'type': 'AIR_POLLUTION_LOW',                   'id': 17,   'descr': {}},  # Pollution low
    {'type': 'AIR_POLLUTION_MEDIUM',                'id': 18,   'descr': {}},  # Pollution medium
    {'type': 'AIR_POLLUTION_HIGH',                  'id': 19,   'descr': {}},  # Pollution high
    {'type': 'AIR_HUMID',                           'id': 20,   'descr': {}},  # Air humid
    {'type': 'AIR_DRY',                             'id': 21,   'descr': {}},  # Air dry
    {'type': 'SOIL_HUMID',                          'id': 22,   'descr': {}},  # Soil humid
    {'type': 'SOIL_DRY',                            'id': 23,   'descr': {}},  # Soil dry
    {'type': 'RAIN_NONE',                           'id': 24,   'descr': {}},  # Rain none
    {'type': 'RAIN_LIGHT',                          'id': 25,   'descr': {}},  # Rain light
    {'type': 'RAIN_HEAVY',                          'id': 26,   'descr': {}},  # Rain heavy
    {'type': 'RAIN_VERY_HEAVY',                     'id': 27,   'descr': {}},  # Rain very heavy
    {'type': 'SUN_NONE',                            'id': 28,   'descr': {}},  # Sun none
    {'type': 'SUN_LIGHT',                           'id': 29,   'descr': {}},  # Sun light
    {'type': 'SUN_HEAVY',                           'id': 30,   'descr': {}},  # Sun heavy
    {'type': 'SNOW_NONE',                           'id': 31,   'descr': {}},  # Snow none
    {'type': 'SNOW_LIGHT',                          'id': 32,   'descr': {}},  # Snow light
    {'type': 'SNOW_HEAVY',                          'id': 33,   'descr': {}},  # Snow heavy
    {'type': 'DEW_POINT',                           'id': 34,   'descr': {}},  # Dew point
    {'type': 'STORM',                               'id': 35,   'descr': {}},  # Storm
    {'type': 'FLOOD',                               'id': 36,   'descr': {}},  # Flood
    {'type': 'EARTHQUAKE',                          'id': 37,   'descr': {}},  # Earthquake
    {'type': 'NUCLEAR_DISASTER',                    'id': 38,   'descr': {}},  # Nuclear disaster
    {'type': 'FIRE',                                'id': 39,   'descr': {}},  # Fire
    {'type': 'LIGHTNING',                           'id': 40,   'descr': {}},  # Lightning
    {'type': 'UV_RADIATION_LOW',                    'id': 41,   'descr': {}},  # UV Radiation low
    {'type': 'UV_RADIATION_MEDIUM',                 'id': 42,   'descr': {}},  # UV Radiation medium
    {'type': 'UV_RADIATION_NORMAL',                 'id': 43,   'descr': {}},  # UV Radiation normal
    {'type': 'UV_RADIATION_HIGH',                   'id': 44,   'descr': {}},  # UV Radiation high
    {'type': 'UV_RADIATION_VERY_HIGH',              'id': 45,   'descr': {}},  # UV Radiation very high
    {'type': 'WARNING_LEVEL1',                      'id': 46,   'descr': {}},  # Warning level 1
    {'type': 'WARNING_LEVEL2',                      'id': 47,   'descr': {}},  # Warning level 2
    {'type': 'WARNING_LEVEL3',                      'id': 48,   'descr': {}},  # Warning level 3
    {'type': 'WARNING_LEVEL4',                      'id': 49,   'descr': {}},  # Warning level 4
    {'type': 'WARNING_LEVEL5',                      'id': 50,   'descr': {}},  # Warning level 5
    {'type': 'ARMAGEDON',                           'id': 51,   'descr': {}},  # Armageddon
    {'type': 'UV_INDEX',                            'id': 52,   'descr': {}},  # UV Index
]
_class_1_weather_forecast = _class_1_weather
_class_1_phone = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'INCOMING_CALL',                       'id': 1,    'descr': {}},  # Incoming call
    {'type': 'OUTGOING_CALL',                       'id': 2,    'descr': {}},  # Outgoing call
    {'type': 'RING',                                'id': 3,    'descr': {}},  # Ring
    {'type': 'ANSWER',                              'id': 4,    'descr': {}},  # Answer
    {'type': 'HANGUP',                              'id': 5,    'descr': {}},  # Hangup
    {'type': 'GIVEUP',                              'id': 6,    'descr': {}},  # Giveup
    {'type': 'TRANSFER',                            'id': 7,    'descr': {}},  # Transfer
    {'type': 'DATABASE_INFO',                       'id': 8,    'descr': {}},  # Database Info
]
_class_1_display = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'CLEAR_DISPLAY',                       'id': 1,    'descr': {}},  # Clear Display
    {'type': 'POSITION_CURSOR',                     'id': 2,    'descr': {}},  # Position cursor
    {'type': 'WRITE_DISPLAY',                       'id': 3,    'descr': {}},  # Write Display
    {'type': 'WRITE_DISPLAY_BUFFER',                'id': 4,    'descr': {}},  # Write Display buffer
    {'type': 'SHOW_DISPLAY_BUFFER',                 'id': 5,    'descr': {}},  # Show Display Buffer
    {'type': 'SET_DISPLAY_BUFFER_PARAM',            'id': 6,    'descr': {}},  # Set Display Buffer Parameter
    {'type': 'SHOW_TEXT',                           'id': 32,   'descr': {}},  # Show Text
    {'type': 'SET_LED',                             'id': 48,   'descr': {}},  # Set LED
    {'type': 'SET_COLOR',                           'id': 49,   'descr': {}},  # Set RGB Color
]
_class_1_remote = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'RC5',                                 'id': 1,    'descr': {}},  # RC5 Send/Receive
    {'type': 'SONY12',                              'id': 3,    'descr': {}},  # SONY 12-bit Send/Receive
    {'type': 'LIRC',                                'id': 32,   'descr': {}},  # LIRC (Linux Infrared Remote Control)
    {'type': 'VSCP',                                'id': 48,   'descr': {}},  # VSCP Abstract Remote Format
    {'type': 'MAPITO',                              'id': 49,   'descr': {}},  # MAPito Remote Format
]
_class_1_configuration = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'LOAD',                                'id': 1,    'descr': {}},  # Load configuration
    {'type': 'LOAD_ACK',                            'id': 2,    'descr': {}},  # Load configuration acknowledge
    {'type': 'LOAD_NACK',                           'id': 3,    'descr': {}},  # Load configuration negative acknowledge
    {'type': 'SAVE',                                'id': 4,    'descr': {}},  # Save configuration
    {'type': 'SAVE_ACK',                            'id': 5,    'descr': {}},  # Save configuration acknowledge
    {'type': 'SAVE_NACK',                           'id': 6,    'descr': {}},  # Save configuration negative acknowledge
    {'type': 'COMMIT',                              'id': 7,    'descr': {}},  # Commit configuration
    {'type': 'COMMIT_ACK',                          'id': 8,    'descr': {}},  # Commit configuration acknowledge
    {'type': 'COMMIT_NACK',                         'id': 9,    'descr': {}},  # Commit configuration negative acknowledge
    {'type': 'RELOAD',                              'id': 10,   'descr': {}},  # Reload configuration
    {'type': 'REALOD_ACK',                          'id': 11,   'descr': {}},  # Reload configuration acknowledge
    {'type': 'RELOAD_NACK',                         'id': 12,   'descr': {}},  # Reload configuration negative acknowledge
    {'type': 'RESTORE',                             'id': 13,   'descr': {}},  # Restore configuration
    {'type': 'RESTORE_ACK',                         'id': 14,   'descr': {}},  # Restore configuration acknowledge
    {'type': 'RESTORE_NACK',                        'id': 15,   'descr': {}},  # Restore configuration negative acknowledge
    {'type': 'SET_PARAMETER',                       'id': 30,   'descr': {}},  # Set parameter
    {'type': 'SET_PARAMETER_DEFAULT',               'id': 31,   'descr': {}},  # Set parameter to default
    {'type': 'SET_PARAMETER_ACK',                   'id': 32,   'descr': {}},  # Set parameter acknowledge
    {'type': 'SET_PARAMETER_NACK',                  'id': 33,   'descr': {}},  # Set paramter negative acknowledge
]
_class_1_gnss = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'POSITION',                            'id': 1,    'descr': {}},  # Position
    {'type': 'SATELLITES',                          'id': 2,    'descr': {}},  # Satellites
]
_class_1_wireless = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'GSM_CELL',                            'id': 1,    'descr': {}},  # GSM Cell
]
_class_1_diagnostic = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'OVERVOLTAGE',                         'id': 1,    'descr': {}},  # Overvoltage
    {'type': 'UNDERVOLTAGE',                        'id': 2,    'descr': {}},  # Undervoltage
    {'type': 'VBUS_LOW',                            'id': 3,    'descr': {}},  # USB VBUS low
    {'type': 'BATTERY_LOW',                         'id': 4,    'descr': {}},  # Battery voltage low
    {'type': 'BATTERY_FULL',                        'id': 5,    'descr': {}},  # Battery full voltage
    {'type': 'BATTERY_ERROR',                       'id': 6,    'descr': {}},  # Battery error
    {'type': 'BATTERY_OK',                          'id': 7,    'descr': {}},  # Battery OK
    {'type': 'OVERCURRENT',                         'id': 8,    'descr': {}},  # Over current
    {'type': 'CIRCUIT_ERROR',                       'id': 9,    'descr': {}},  # Circuit error
    {'type': 'SHORT_CIRCUIT',                       'id': 10,   'descr': {}},  # Short circuit
    {'type': 'OPEN_CIRCUIT',                        'id': 11,   'descr': {}},  # Open Circuit
    {'type': 'MOIST',                               'id': 12,   'descr': {}},  # Moist
    {'type': 'WIRE_FAIL',                           'id': 13,   'descr': {}},  # Wire failure
    {'type': 'WIRELESS_FAIL',                       'id': 14,   'descr': {}},  # Wireless faliure
    {'type': 'IR_FAIL',                             'id': 15,   'descr': {}},  # IR failure
    {'type': '1WIRE_FAIL',                          'id': 16,   'descr': {}},  # 1-wire failure
    {'type': 'RS222_FAIL',                          'id': 17,   'descr': {}},  # RS-222 failure
    {'type': 'RS232_FAIL',                          'id': 18,   'descr': {}},  # RS-232 failure
    {'type': 'RS423_FAIL',                          'id': 19,   'descr': {}},  # RS-423 failure
    {'type': 'RS485_FAIL',                          'id': 20,   'descr': {}},  # RS-485 failure
    {'type': 'CAN_FAIL',                            'id': 21,   'descr': {}},  # CAN failure
    {'type': 'LAN_FAIL',                            'id': 22,   'descr': {}},  # LAN failure
    {'type': 'USB_FAIL',                            'id': 23,   'descr': {}},  # USB failure
    {'type': 'WIFI_FAIL',                           'id': 24,   'descr': {}},  # Wifi failure
    {'type': 'NFC_RFID_FAIL',                       'id': 25,   'descr': {}},  # NFC/RFID failure
    {'type': 'LOW_SIGNAL',                          'id': 26,   'descr': {}},  # Low signal
    {'type': 'HIGH_SIGNAL',                         'id': 27,   'descr': {}},  # High signal
    {'type': 'ADC_FAIL',                            'id': 28,   'descr': {}},  # ADC failure
    {'type': 'ALU_FAIL',                            'id': 29,   'descr': {}},  # ALU failure
    {'type': 'ASSERT',                              'id': 30,   'descr': {}},  # Assert
    {'type': 'DAC_FAIL',                            'id': 31,   'descr': {}},  # DAC failure
    {'type': 'DMA_FAIL',                            'id': 32,   'descr': {}},  # DMA failure
    {'type': 'ETH_FAIL',                            'id': 33,   'descr': {}},  # Ethernet failure
    {'type': 'EXCEPTION',                           'id': 34,   'descr': {}},  # Exception
    {'type': 'FPU_FAIL',                            'id': 35,   'descr': {}},  # FPU failure
    {'type': 'GPIO_FAIL',                           'id': 36,   'descr': {}},  # GPIO failure
    {'type': 'I2C_FAIL',                            'id': 37,   'descr': {}},  # I2C failure
    {'type': 'I2S_FAIL',                            'id': 38,   'descr': {}},  # I2S failure
    {'type': 'INVALID_CONFIG',                      'id': 39,   'descr': {}},  # Invalid configuration
    {'type': 'MMU_FAIL',                            'id': 40,   'descr': {}},  # MMU failure
    {'type': 'NMI',                                 'id': 41,   'descr': {}},  # NMI failure
    {'type': 'OVERHEAT',                            'id': 42,   'descr': {}},  # Overheat
    {'type': 'PLL_FAIL',                            'id': 43,   'descr': {}},  # PLL fail
    {'type': 'POR_FAIL',                            'id': 44,   'descr': {}},  # POR failure
    {'type': 'PWM_FAIL',                            'id': 45,   'descr': {}},  # PWM failure
    {'type': 'RAM_FAIL',                            'id': 46,   'descr': {}},  # RAM failure
    {'type': 'ROM_FAIL',                            'id': 47,   'descr': {}},  # ROM failure
    {'type': 'SPI_FAIL',                            'id': 48,   'descr': {}},  # SPI failure
    {'type': 'STACK_FAIL',                          'id': 49,   'descr': {}},  # Stack failure
    {'type': 'LIN_FAIL',                            'id': 50,   'descr': {}},  # LIN bus failure
    {'type': 'UART_FAIL',                           'id': 51,   'descr': {}},  # UART failure
    {'type': 'UNHANDLED_INT',                       'id': 52,   'descr': {}},  # Unhandled interrupt
    {'type': 'MEMORY_FAIL',                         'id': 53,   'descr': {}},  # Memory failure
    {'type': 'VARIABLE_RANGE',                      'id': 54,   'descr': {}},  # Variable range failure
    {'type': 'WDT',                                 'id': 55,   'descr': {}},  # WDT failure
    {'type': 'EEPROM_FAIL',                         'id': 56,   'descr': {}},  # EEPROM failure
    {'type': 'ENCRYPTION_FAIL',                     'id': 57,   'descr': {}},  # Encryption failure
    {'type': 'BAD_USER_INPUT',                      'id': 58,   'descr': {}},  # Bad user input failure
    {'type': 'DECRYPTION_FAIL',                     'id': 59,   'descr': {}},  # Decryption failure
    {'type': 'NOISE',                               'id': 60,   'descr': {}},  # Noise
    {'type': 'BOOTLOADER_FAIL',                     'id': 61,   'descr': {}},  # Boot loader failure
    {'type': 'PROGRAMFLOW_FAIL',                    'id': 62,   'descr': {}},  # Program flow failure
    {'type': 'RTC_FAIL',                            'id': 63,   'descr': {}},  # RTC faiure
    {'type': 'SYSTEM_TEST_FAIL',                    'id': 64,   'descr': {}},  # System test failure
    {'type': 'SENSOR_FAIL',                         'id': 65,   'descr': {}},  # Sensor failure
    {'type': 'SAFESTATE',                           'id': 66,   'descr': {}},  # Safe state entered
    {'type': 'SIGNAL_IMPLAUSIBLE',                  'id': 67,   'descr': {}},  # Signal implausible
    {'type': 'STORAGE_FAIL',                        'id': 68,   'descr': {}},  # Storage fail
    {'type': 'SELFTEST_FAIL',                       'id': 69,   'descr': {}},  # Self test OK
    {'type': 'ESD_EMC_EMI',                         'id': 70,   'descr': {}},  # ESD/EMC/EMI failure
    {'type': 'TIMEOUT',                             'id': 71,   'descr': {}},  # Timeout
    {'type': 'LCD_FAIL',                            'id': 72,   'descr': {}},  # LCD failure
    {'type': 'TOUCHPANEL_FAIL',                     'id': 73,   'descr': {}},  # Touch panel failure
    {'type': 'NOLOAD',                              'id': 74,   'descr': {}},  # No load
    {'type': 'COOLING_FAIL',                        'id': 75,   'descr': {}},  # Cooling failure
    {'type': 'HEATING_FAIL',                        'id': 76,   'descr': {}},  # Heating failure
    {'type': 'TX_FAIL',                             'id': 77,   'descr': {}},  # Transmission failure
    {'type': 'RX_FAIL',                             'id': 78,   'descr': {}},  # Receiption failure
    {'type': 'EXT_IC_FAIL',                         'id': 79,   'descr': {}},  # External IC failure
    {'type': 'CHARGING_ON',                         'id': 80,   'descr': {}},  # Charging of battery or similar has started or is in progress
    {'type': 'CHARGING_OFF',                        'id': 81,   'descr': {}},  # Charging of battery or similar has ended
]
_class_1_error = [
    {'type': 'SUCCESS',                             'id': 0,    'descr': {}},  # Success
    {'type': 'ERROR',                               'id': 1,    'descr': {}},  # Error
    {'type': 'CHANNEL',                             'id': 7,    'descr': {}},  # Channel error
    {'type': 'FIFO_EMPTY',                          'id': 8,    'descr': {}},  # Fifo empty error
    {'type': 'FIFO_FULL',                           'id': 9,    'descr': {}},  # Fifo full error
    {'type': 'FIFO_SIZE',                           'id': 10,   'descr': {}},  # Fifo size error
    {'type': 'FIFO_WAIT',                           'id': 11,   'descr': {}},  # Fifo wait error
    {'type': 'GENERIC',                             'id': 12,   'descr': {}},  # Generic error
    {'type': 'HARDWARE',                            'id': 13,   'descr': {}},  # Hardware error
    {'type': 'INIT_FAIL',                           'id': 14,   'descr': {}},  # initialization error
    {'type': 'INIT_MISSING',                        'id': 15,   'descr': {}},  # Missing initialization error
    {'type': 'INIT_READY',                          'id': 16,   'descr': {}},  # Initialization ready
    {'type': 'NOT_SUPPORTED',                       'id': 17,   'descr': {}},  # Not supported
    {'type': 'OVERRUN',                             'id': 18,   'descr': {}},  # Overrun error
    {'type': 'RCV_EMPTY',                           'id': 19,   'descr': {}},  # Receiver empty error
    {'type': 'REGISTER',                            'id': 20,   'descr': {}},  # Register error
    {'type': 'TRM_FULL',                            'id': 21,   'descr': {}},  # Transmitter full error
    {'type': 'LIBRARY',                             'id': 28,   'descr': {}},  # Library error
    {'type': 'PROCADDRESS',                         'id': 29,   'descr': {}},  # Procedural address error
    {'type': 'ONLY_ONE_INSTANCE',                   'id': 30,   'descr': {}},  # Only one instance error
    {'type': 'SUB_DRIVER',                          'id': 31,   'descr': {}},  # Sub driver error
    {'type': 'TIMEOUT',                             'id': 32,   'descr': {}},  # Timeout error
    {'type': 'NOT_OPEN',                            'id': 33,   'descr': {}},  # Not open error
    {'type': 'PARAMETER',                           'id': 34,   'descr': {}},  # Parameter error
    {'type': 'MEMORY',                              'id': 35,   'descr': {}},  # Memory error
    {'type': 'INTERNAL',                            'id': 36,   'descr': {}},  # Internal error
    {'type': 'COMMUNICATION',                       'id': 37,   'descr': {}},  # Communication error
    {'type': 'USER',                                'id': 38,   'descr': {}},  # User error
    {'type': 'PASSWORD',                            'id': 39,   'descr': {}},  # Password error
    {'type': 'CONNECTION',                          'id': 40,   'descr': {}},  # Connection error
    {'type': 'INVALID_HANDLE',                      'id': 41,   'descr': {}},  # Invalid handle error
    {'type': 'OPERATION_FAILED',                    'id': 42,   'descr': {}},  # Operation failed error
    {'type': 'BUFFER_SMALL',                        'id': 43,   'descr': {}},  # Supplied buffer is to small to fit content
    {'type': 'ITEM_UNKNOWN',                        'id': 44,   'descr': {}},  # Requested item is unknown
    {'type': 'NAME_USED',                           'id': 45,   'descr': {}},  # Name is already in use
    {'type': 'DATA_WRITE',                          'id': 46,   'descr': {}},  # Error when writing data
    {'type': 'ABORTED',                             'id': 47,   'descr': {}},  # Operation stopped or aborted
    {'type': 'INVALID_POINTER',                     'id': 48,   'descr': {}},  # Pointer with invalid value
]
_class_1_log = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
    {'type': 'MESSAGE',                             'id': 1,    'descr': {}},  # Log event
    {'type': 'START',                               'id': 2,    'descr': {}},  # Log Start
    {'type': 'STOP',                                'id': 3,    'descr': {}},  # Log Stop
    {'type': 'LEVEL',                               'id': 4,    'descr': {}},  # Log Level

]
_class_1_laboratory = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_class_1_local = [
    {'type': 'GENERAL',                             'id': 0,    'descr': {}},  # General event
]
_vscp_class_1_dict = [
    {'class': 'CLASS1.PROTOCOL',            'id': 0,    'types': _class_1_protocol},            # VSCP Protocol Functionality
    {'class': 'CLASS1.ALARM',               'id': 1,    'types': _class_1_alarm},               # Alarm functionality
    {'class': 'CLASS1.SECURITY',            'id': 2,    'types': _class_1_security},            # Security
    {'class': 'CLASS1.MEASUREMENT',         'id': 10,   'types': _class_1_measurement},         # Measurement
    {'class': 'CLASS1.MEASUREMENTX1',       'id': 11,   'types': _class_1_measurement_x1},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX2',       'id': 12,   'types': _class_1_measurement_x2},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX3',       'id': 13,   'types': _class_1_measurement_x3},      # Measurement
    {'class': 'CLASS1.MEASUREMENTX4',       'id': 14,   'types': _class_1_measurement_x4},      # Measurement
    {'class': 'CLASS1.DATA',                'id': 15,   'types': _class_1_data},                # Data
    {'class': 'CLASS1.INFORMATION',         'id': 20,   'types': _class_1_information},         # Information
    {'class': 'CLASS1.CONTROL',             'id': 30,   'types': _class_1_control},             # Control
    {'class': 'CLASS1.MULTIMEDIA',          'id': 40,   'types': _class_1_multimedia},          # Multimedia
    {'class': 'CLASS1.AOL',                 'id': 50,   'types': _class_1_aol},                 # Alert On LAN
    {'class': 'CLASS1.MEASUREMENT64',       'id': 60,   'types': _class_1_measurement_64},      # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X1',     'id': 61,   'types': _class_1_measurement_64_x1},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X2',     'id': 62,   'types': _class_1_measurement_64_x2},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X3',     'id': 63,   'types': _class_1_measurement_64_x3},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT64X4',     'id': 64,   'types': _class_1_measurement_64_x4},   # Double precision floating point measurement
    {'class': 'CLASS1.MEASUREZONE',         'id': 65,   'types': _class_1_measure_zone},        # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX1',       'id': 66,   'types': _class_1_measure_zone_x1},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX2',       'id': 67,   'types': _class_1_measure_zone_x2},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX3',       'id': 68,   'types': _class_1_measure_zone_x3},     # Measurement with zone
    {'class': 'CLASS1.MEASUREZONEX4',       'id': 69,   'types': _class_1_measure_zone_x4},     # Measurement with zone
    {'class': 'CLASS1.MEASUREMENT32',       'id': 70,   'types': _class_1_measurement_32},      # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X1',     'id': 71,   'types': _class_1_measurement_32_x1},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X2',     'id': 72,   'types': _class_1_measurement_32_x2},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X3',     'id': 73,   'types': _class_1_measurement_32_x3},   # Single precision floating point measurement
    {'class': 'CLASS1.MEASUREMENT32X4',     'id': 74,   'types': _class_1_measurement_32_x4},   # Single precision floating point measurement
    {'class': 'CLASS1.SETVALUEZONE',        'id': 85,   'types': _class_1_set_value_zone},      # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX1',      'id': 86,   'types': _class_1_set_value_zone_x1},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX2',      'id': 87,   'types': _class_1_set_value_zone_x2},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX3',      'id': 88,   'types': _class_1_set_value_zone_x3},   # Set value with zone
    {'class': 'CLASS1.SETVALUEZONEX4',      'id': 89,   'types': _class_1_set_value_zone_x4},   # Set value with zone
    {'class': 'CLASS1.WEATHER',             'id': 90,   'types': _class_1_weather},             # Weather
    {'class': 'CLASS1.WEATHER_FORECAST',    'id': 95,   'types': _class_1_weather_forecast},    # Weather forecast
    {'class': 'CLASS1.PHONE',               'id': 100,  'types': _class_1_phone},               # Phone
    {'class': 'CLASS1.DISPLAY',             'id': 102,  'types': _class_1_display},             # Display
    {'class': 'CLASS1.IR',                  'id': 110,  'types': _class_1_remote},              # IR Remote I/f
    {'class': 'CLASS1.CONFIGURATION',       'id': 120,  'types': _class_1_configuration},       # Configuration
    {'class': 'CLASS1.GNSS',                'id': 206,  'types': _class_1_gnss},                # Position (GNSS)
    {'class': 'CLASS1.WIRELESS',            'id': 212,  'types': _class_1_wireless},            # Wireless
    {'class': 'CLASS1.DIAGNOSTIC',          'id': 506,  'types': _class_1_diagnostic},          # Diagnostic
    {'class': 'CLASS1.ERROR',               'id': 508,  'types': _class_1_error},               # Error
    {'class': 'CLASS1.LOG',                 'id': 509,  'types': _class_1_log},                 # Logging
    {'class': 'CLASS1.LABORATORY',          'id': 510,  'types': _class_1_laboratory},          # Laboratory use
    {'class': 'CLASS1.LOCAL',               'id': 511,  'types': _class_1_local}                # Local use
]
