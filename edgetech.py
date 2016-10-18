""" A package for communicating with the DewMaster from Edgetech Instruments

The DewMaster is a device sold by Edgetech instruments for measuring moisture levels in gas
streams.  Since the device relies on a simple physical principle for measuring dewpoint, it has
a huge dynamic range and is capable of measuring moisture content from the ~10 ppm level to the
100% RH level.

The Edgetech communication was clearly designed for a human to be typing at a terminal window
which gives it some odd features.  Namely, when a command is entered, the device will respond with
'INPUT: X' where X is the first letter entered.  To initiate the command a seperate command must
then be sent with the second and third (or more) letters and the endline characters.
"""

import serial
import warnings
from time import time, sleep

__author__ = "Chris Mueller"
__email__ = "chrisark7@gmail.com"
__status__ = "Development"


class DewMaster:
    """ A class for communicating with the Edgetech Instruments DewMaster
    """
    def __init__(self, port, timeout=2):
        """
         :param port: The COM port to which the DewMaster is connected (i.e. 'COM2' or simply 2)
         :param timeout: The length of time in seconds to wait before timing out when communicating
         :type port: int or str
         :type timeout: int
        """
        # Try to connect to the port
        try:
            self.device = serial.Serial(port, baudrate=9600, bytesize=serial.EIGHTBITS,
                                        stopbits=serial.STOPBITS_ONE, parity=serial.PARITY_NONE,
                                        timeout=timeout)
        except serial.SerialException as e:
            print('Unable to connect to port ' + port + '. Error message: ' + e.__str__())
            raise
        # Check the status
        self.read()
        sleep(0.2)
        self.write('ST')
        out = self.read()
        if not out:
            warnings.warn('Device did not repond to status query')
        else:
            print(out.replace('\r', '').replace('Press ENTER to continue.....', ''))

    def write(self, command):
        """ Writes a command to the DewMaster

        :param command: a string command
        :type command: str
        """
        # Send letters of command
        for char in command:
            self.device.write(char.encode(encoding='utf-8'))
            self.read()
        # Send ENTER
        self.device.write('\r\n'.encode(encoding='utf-8'))

    def read(self):
        """ Waits for the timeout period for the DewMaster to send data
        """
        # Get start time and define stop time
        t_now = time()
        t_stop = t_now + self.device.timeout
        last_val = 0
        out = ''.encode(encoding='utf-8')
        while t_now < t_stop:
            now_val = self.device.in_waiting
            if now_val > 0 and now_val == last_val:
                out = self.device.read(now_val)
                break
            else:
                last_val = now_val
            sleep(0.05)
            t_now = time()
        else:
            warnings.warn('read attempt timed out')
        return out.decode(encoding='utf-8').strip()








