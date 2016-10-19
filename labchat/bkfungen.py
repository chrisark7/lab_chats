""" A package for communicating with the BK Precision function generators

This package relies on the pyvisa package (which relies on the NI Visa package in turn) for
communication with the function generators.
"""

import logging
from time import sleep
import visa

__author__ = "Chris Mueller and Mingcan Chen"
__email__ = "chrisark7@gmail.com"
__status__ = "Development"

logger = logging.getLogger(__name__)


class BKFunGen(object):
    """ A class for communicating with the BK Precision function generators

    This class relies on the pyvisa package for communication, which, in turn, relies on the
    third party NI visa package.

    Commands for the function generator can be found in the 'programmer's manual' for the specific
    model.
    """
    def __init__(self, device_id=0, timeout=0.5):
        """ The constructor for the FuncGen class

        This function searches the devices connected to the computer and initializes the Scope
        object with one of them.  Note that it is still necessary to open the connection before
        being able to interact with the scope.

        The list of devices connected to the computer will be printed to the log.

        :param device_id: Integer or string which describes the device to connect to
        :param timeout: The default timeout value to use when interacting with the scope in seconds
        :type device_id: int or str
        :type timeout: int or float
        :return: An instance of the BKFuncGen class
        :rtype: BKFunGen
        """
        # Get list of devices connected to the computer
        rm = visa.ResourceManager()
        devices = rm.list_resources()
        # Check device list
        if not devices:
            raise LookupError('no devices are connected to the computer')
        # Parse device_id and assign
        if type(device_id) is str:
            if device_id not in devices:
                raise ValueError('device_id is not in list of devices')
            else:
                fungen_id = device_id
        elif type(device_id) is not int:
            try:
                device_id = int(device_id)
            except:
                raise ValueError('device_id should be a string or an integer')
            if device_id > len(devices) - 1:
                raise ValueError('device_id is largerh than the number of devices')
            else:
                fungen_id = devices[device_id]
        elif device_id > len(devices) - 1:
            raise ValueError('device_id is larger than the number of devices')
        else:
            fungen_id = devices[device_id]
        # Print chosen device
        logger.info('Initializing device: {0}'.format(fungen_id))
        # Set parameters
        self.timeout = timeout*1e3
        self.fungen_id = fungen_id
        self.resource_manager = rm
        self.is_open = False
        self.device = None

    ###############################################################################################
    # Low level commands
    ###############################################################################################
    def open(self):
        """ Opens the connection to the function generator
        """
        if self.is_open:
            raise IOError('Comunication to function generator is already open')
        try:
            self.device = self.resource_manager.open_resource(self.fungen_id, open_timeout=10e3)
        except:
            raise IOError('Unable to open connection to function generator')
        self.is_open = True
        self.write('COMM_HEADER LONG')
        idstr = self.query('*IDN?')
        logger.info('Successfully opened communication to device: {0}'.format(idstr))
        self.device.timeout = self.timeout

    def close(self):
        """ Closes the connection to the function generator
        """
        if not self.is_open:
            raise IOError('Communication to function generator is already closed')
        self.device.close()
        self.is_open = False

    def flush(self):
        """ Flushes the input and output buffers
        """
        if not self.is_open:
            raise IOError('Communication to function generator is closed')
        self.device.flush(mask=64)
        self.device.flush(mask=128)

    def write(self, command):
        """ Writes a command to the function generator

        :param command: A valid command to the function generator
        :type command: str
        :return: the output of the write command
        :rtype: str
        """
        if not self.is_open:
            raise IOError('Communication to function generator is closed')
        try:
            sleep(0.1)
            out = self.device.write(command)
        except visa.VisaIOError:
            raise ValueError('Command timed out; most likely it is not a valid command')
        return out

    def read(self):
        """ Reads the most recent output from the function generator

        :param timeout: The timeout length in seconds
        :type timeout: float
        :return: The output of the read command
        :rtype: str
        """
        if not self.is_open:
            raise IOError('Communication to function generator is closed')
        try:
            out = self.device.read()
        except visa.VisaIOError:
            logger.debug('Device did not return anything, sleeping for 0.5 seconds and trying again')
            sleep(0.5)
            try:
                out = self.device.read()
            except visa.VisaIOError:
                out = ''
                logger.warn('Device did not return anything when trying to read')
        return out.rstrip()

    def query(self, command):
        """ Queries a value from the function generator

        This method is equivalent to writing a query command and then reading the function
        generator's output.

        :param command: A valid command to the function generator
        :type command: str
        :return: the output of the query command
        :rtype: str
        """
        self.write(command)
        out = self.read()
        return out

    ###############################################################################################
    #  High Level Commands
    ###############################################################################################
    def set_output(self, channel=1, on_off=None, load=None):
        """ Sets the output settings of the function generator

        Any parameter left as ``None`` will not be changed from its current state.

        The ``channel`` parameter must be either ``1`` or ``2`` for the two output channels of the
        function generator.

        The ``on_off`` parameter determines whether to set the output to be on or off.  The two
        valid settings for it are ``'ON'`` or ``'OFF'``.

        The ``load`` parameter determines wether the output impedance is set to 50 Ohms or High Z.
        The two valid inputs are ``50`` or ``HZ``.

        :param channel: 1 or 2
        :param on_off: 'ON' of 'OFF'
        :param load: 50 or 'HZ'
        :type channel: int
        :type on_off: str
        :type load: int or str
        :return:
        """
        # Type checking
        if channel not in [1, 2]:
            raise ValueError('channel paramter should be 1 or 2')
        if on_off not in ['ON', 'On', 'on', 'OFF', 'Off', 'off', None]:
            raise ValueError('on_off paramter should be ``ON`` or ``OFF``')
        if load not in [50, '50', 'HZ', 'hz', 'Hz', None]:
            raise ValueError('load parameter should be 50 or ``HZ``')
        # Build command
        command = 'C{0:0.0f}:OUTPUT'.format(channel)
        if on_off is not None:
            command += ' ' + on_off.upper()
            if load is not None:
                command += ',LOAD,' + str(load).upper()
        elif load is not None:
            command += ' LOAD,' + str(load).upper()
        else:
            raise ValueError('No parameters were specified.  Nothing to set')
        # Send command
        logger.debug('Command: {0}'.format(command))
        self.write(command)

    def get_output(self, channel=1):
        """ Returns the output settings of the function generator as a string.

        This method simply queries the function generator with the ``'C1:OUTPUT?'`` command (or
        'C2' for channel 2) and returns the resulting string.

        :return: Output settings as string
        :rtype: str
        """
        # Type checking
        if channel not in [1, 2]:
            raise ValueError('channel paramter should be 1 or 2')
        # Build command
        command = 'C{0:0.0f}:OUTPUT?'.format(channel)
        # Query and return
        out = self.query(command)
        return out

    def set_wave(self, channel=1, wavetype=None, frequency=None, amplitude=None, offset=None,
                 symmetry=None, duty=None, phase=None, variance=None, mean=None, delay=None):
        """ Sets the basic wave parameters of the scope

        Any parameters left as ``None`` will not be changed from the current state.  Note that
        many of the parameters are only valid for some wavetypes.

        :param channel: 1 or 2
        :param wavetype: 'SINE', 'SQUARE', 'RAMP', 'PULSE', 'NOISE', 'ARB', or 'DC'
        :param frequency: unit is Hertz, minimum is 1e-6, max is 25e6
        :param amplitude: unit is Volts
        :param offset: unit is Volts
        :param symmetry: unit is percent, only for ramp wave, 0-100
        :param duty: unit is percent, 20-80 for square wave, 0.1-99.9 for pulse
        :param phase: unit is degrees, 0-360
        :param variance: unit is Volts, only for noise wave
        :param mean: unit is Volts, only for noise wave
        :param delay: unit is seconds
        :type channel: int
        :type wavetype: str
        :type frequency: float
        :type amplitude: float
        :type offset: float
        :type symmetry: float
        :type duty: float
        :type phase: float
        :type variance: float
        :type mean: float
        :type delay: float
        """
        # Type checking
        if channel not in [1, 2]:
            raise ValueError('channel parameter should be 1 or 2')
        if wavetype is not None:
            if wavetype.upper() not in ['SINE', 'SQUARE', 'RAMP', 'PULSE', 'NOISE', 'ARB', 'DC', None]:
                raise ValueError('wavetype parameter should be SINE, SQUARE, RAMP, PULSE, NOISE, ARB, or DC')
        if frequency is not None:
            if not (1e-6 <= frequency <= 25e6):
                raise ValueError('frequency parameter should be between 1e-6 and 25e6')
        if amplitude is not None:
            if amplitude < 0.004:
                raise ValueError('amplitude parameter should not be less than 0.004')
        # Build command
        command_dict = {'WVTP': wavetype, 'FRQ': frequency, 'AMP': amplitude, 'OFST': offset,
                        'SYM': symmetry, 'DUTY': duty, 'PHSE': phase, 'VAR': variance, 'MEAN': mean,
                        'DLY': delay}
        if all([command_dict[key] is None for key in command_dict]):
            raise ValueError('No parameters were specified.  Nothing to set')
        command = 'C{0:0.0f}:BASIC_WAVE '.format(channel)
        for key in command_dict:
            if command_dict[key] is not None:
                command += '{0},{1},'.format(key, command_dict[key])
        # Remove trailing comma
        command = command[:-1]
        # Send command
        logger.debug('Command: {0}'.format(command))
        self.write(command)

    def get_wave(self, channel=1):
        """ Returns the basic wave settings of the function generator as a string.

        This method simply queries the function generator with the ``'C1:BASIC_WAVE?'`` command (or
        'C2' for channel 2) and returns the resulting string.

        :return: Output settings as string
        :rtype: str
        """
        # Type checking
        if channel not in [1, 2]:
            raise ValueError('channel paramter should be 1 or 2')
        # Build command
        command = 'C{0:0.0f}:BASIC_WAVE?'.format(channel)
        # Query and return
        out = self.query(command)
        return out



