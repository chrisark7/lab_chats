""" A package for controlling the RS232 switching relay.

This package is designed specifically to work with the NCD R120HPRS switching relay, but may
also work with other devices from National Control Dynamics.

Note that the relays only understand ascii (latin_1) encoded messages.  Read the manual for more
details.
"""

import serial
from time import sleep

__author__ = "Chris Mueller and Mingcan Chen"
__email__ = "cmueller@a-optowave.com"
__status__ = "Development"


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
        # Try to connect to the port
        try:
            self.device = serial.Serial(port, baudrate=9600, bytesize=serial.EIGHTBITS,
                                        stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE,
                                        timeout=timeout)
        except serial.SerialException as e:
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
        if not self.device.isOpen():
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
        out = self.device.write(chr(code).encode(encoding='latin_1'))
        return out

    def read(self):
        """ Reads a message from the device one byte at a time

        :return: The ascii character code coresponding to the read message
        :rtype: int
        """
        if not self.is_open:
            raise IOError('Device is not open')
        if self.device.inWaiting() == 0:
            raise IOError('No data in read buffer')
        else:
            out = self.device.read(size=1)
        return ord(out)

    ###############################################################################################
    # Commands
    ###############################################################################################
    def turn_on(self):
        """ Turns the relay on
        """
        self.write(254)
        self.write(1)

    def turn_off(self):
        """ Turns the relay off
        """
        self.write(254)
        self.write(0)

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