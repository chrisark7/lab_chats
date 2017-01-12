""" A package for controlling the RS232 switching relay.

This package is designed specifically to work with the NCD R120HPRS switching relay, but may
also work with other devices from National Control Dynamics.

Note that the relays only understand ascii (latin_1) encoded messages.  Read the manual for more
details.
"""

from time import sleep
import logging
import warnings
import pyvisa

__author__ = "Chris Mueller and Mingcan Chen"
__email__ = "cmueller@a-optowave.com"
__status__ = "Development"


logger = logging.getLogger(__name__)

class Relay(object):
    """ A class for working with the National Control Dynamics R120HPRS switching relay.
    """
    def __init__(self, port, timeout=2):
        """

        :param port: The name of the port to which the NCD device is connected
        :type port: str
        :return: An instance of the Relay class
        :rtype: Relay
        """
        # Create resource manager
        rm = pyvisa.ResourceManager()
        # Parse the port
        if type(port) is str:
            if port[0:3].upper() == 'COM':
                try:
                    port = int(port[3:])
                except ValueError:
                    logger.error('Port is improperly specified')
                    raise
        if type(port) is int:
            port = "ASRL{0}::INSTR".format(port)
            logger.debug("Port was changed to: {0}".format(port))
        # Try to connect to the port
        try:
            self.device = rm.open_resource(port,
                                           baud_rate=9600,
                                           data_bits=8,
                                           stop_bits=pyvisa.constants.StopBits.one,
                                           parity=pyvisa.constants.Parity.none,
                                           timeout=timeout*1e3,
                                           encoding='latin_1',
                                           read_termination="\n",
                                           write_termination="\n",
                                           chunk_size=1)
        except pyvisa.VisaIOError:
            print('Unable to connect to port ' + port + '. Error message: ' + e.__str__())
            raise
        self.is_open = False

    ###############################################################################################
    # Open, Close, Read, and Write
    ###############################################################################################
    def open(self):
        """ Opens communication to the device
        """
        # Check that serial communication is open
        self.device.open()
        # Set flag
        self.is_open = True
        # Enable commands to be sent to the relay
        self.write(254)
        self.write(248)

    def close(self):
        """ Closes communication to the device
        """
        self.device.close()
        self.is_open = False

    def write(self, code):
        """ Sends a code to the device.

        :param code: a numerical code between 0 and 255
        :type code: int
        :return: returns anything returned by the write command, usually an integer
        :rtype: int
        """
        # Check if communication is open
        if not self.is_open:
            raise IOError('Communication to device is not open')
        # Check that code is an integer between 0 and 255
        if type(code) is not int:
            raise TypeError('code should be an integer between 0 and 255')
        if code > 255 or code < 0:
            raise ValueError('code should be an integer between 0 and 255')
        # Send command
        self.device.write_raw(chr(code).encode(encoding='latin_1'))

    def read(self):
        """ Reads a message from the device one byte at a time

        :return: The ascii character code coresponding to the read message
        :rtype: int
        """
        if not self.is_open:
            raise IOError('Device is not open')
        if self.device.bytes_in_buffer == 0:
            raise IOError('No data in read buffer')
        else:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                out = self.device.visalib.read(self.device.session, 1)[0]
        return ord(out)

    ###############################################################################################
    # Commands
    ###############################################################################################
    def turn_on(self):
        """ Turns the relay on
        """
        self.write(254)
        self.write(1)
        if self.get_state() == 1:
            return True
        else:
            return False

    def turn_off(self):
        """ Turns the relay off
        """
        self.write(254)
        self.write(0)
        if self.get_state() == 0:
            return True
        else:
            return False

    def get_state(self):
        """ Returns the relay state: 0=off, 1=on

        :return: 0 for off, 1 for on
        :rtype: int
        """
        self.write(254)
        self.write(4)
        sleep(0.1)
        return self.read()

    def set_default_state(self):
        """ Sets the current state of the relay to be the default state
        """
        self.write(254)
        self.write(8)
        if self.get_default_state() in [1, 3]:
            return True
        else:
            return False

    def get_default_state(self):
        """ Returns the current default state of the relay.

        0: relay 1 and 2 off at startup
        1: relay 1 on, relay 2 off at startup
        2: relay 1 off, relay 1 on at startup
        3: relay 1 and 2 on at startup

        Most of our devices only have a single relay, relay 1
        """
        self.write(254)
        self.write(9)
        sleep(0.1)
        return self.read()
