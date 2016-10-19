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
import re
from datetime import datetime
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
        sleep(0.5)
        out = self.get_status(print_status=False)
        if not out:
            warnings.warn('Device did not repond to status query')
        else:
            print(out)

    ###############################################################################################
    # Core Communication Methods
    ###############################################################################################
    def open(self):
        """ Opens communication to the DewMaster
        """
        if not self.device.is_open:
            self.device.open()

    def close(self):
        """ Closes communication with the DewMaster
        """
        self.device.close()

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
        """ Reads from the DewMaster

        This method waits for the DewMaster to be ready to send a message for up to the specified
        timeout period.  If the DewMaster does not return any data, then it returns a blank string
        and prints a warning.
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

    ###############################################################################################
    # Get/Set commands
    ###############################################################################################
    def get_status(self, print_status=True):
        """ Returns a system status report

        If `print_status` is True, then the system status report will be printed to the screen.

        :param print_status: If True, then the report is printed to the screen
        :type print_status: bool
        :return: System status report string
        :rtype: str
        """
        # Read system status
        self.write('ST')
        out = self.read()
        # Send enter and read poll output
        self.write('')
        self.read()
        self.read()
        # Format printout and print
        out = out.replace('\r', '').replace('Press ENTER to continue.....', '')
        if print_status:
            print(out)
        return out

    def set_average(self, avg_num):
        """ Sets the number of averages for each reading

        The range of values allowed is 1 to 16
        """
        # Check type
        if type(avg_num) is not int:
            try:
                avg_num = int(avg_num)
            except ValueError:
                print('avg_num should be an integer')
                raise
        if avg_num < 1 or avg_num > 16:
            raise ValueError('avg_num should be between 1 and 16')
        # Issue average command and read output
        self.write('AV')
        self.read()
        self.write(str(avg_num))
        out = self.read()
        self.read()
        # Check output
        match = re.search(r"Number of data points to average = (\d+)", out)
        if not match:
            warnings.warn('Average value may not have been set properly')
        elif not int(match.group(1)) == avg_num:
            warnings.warn('Average was set to {0} instead of {1}'.format(match.group(1), avg_num))

    def set_output_interval(self, interval):
        """ Sets the data output interval in seconds

        :param interval: The output interval in seocnds
        :type interval: int
        """
        # Check type
        if type(interval) is not int:
            warnings.warn('interval should be an even number of seconds')
            try:
                interval = int(interval)
            except:
                raise TypeError('interval should be an integer')
        if interval < 1:
            raise ValueError('interval should be greater than zero')
        # Set the output interval
        self.write('O')
        self.read()
        self.write(str(interval))
        out = self.read()
        self.read()
        # Check output
        match = re.search(r"The new serial interval is (\d+)", out)
        if not match:
            warnings.warn('Interval may not have been set properly')
        elif not int(match.group(1)) == interval:
            warnings.warn('Interval was set to {0} instead of {1}'.format(match.group(1), interval))

    ###############################################################################################
    # Data Collection
    ###############################################################################################
    @staticmethod
    def _parse_data(data_str):
        """ Parses the data string returned by the DewMaster when it is polled

        :param data_str: A data string from the DewMaster
        :type data_str: str
        :return: (time stamp, list of measurements, list of data values, measurement state)
        :rtype: (datetime.datetime, list of str, list of float, str)
        """
        # Check for multiple lines
        if re.search('\r\n', data_str):
            warnings.warn('data_str has multiple lines, using the first recognized data line')
            for data_n in data_str.split('\r\n'):
                if re.search(r"([A-Z]+)\s+=\s+([-\d\.]+)", data_str):
                    data_str = data_n
                    break
            else:
                raise ValueError('{0} does not appear to contain any data'.format(data_str))
        # Create datetime object
        match = re.search(r"(\d\d/?){3}\s+(\d\d:?){3}", data_str)
        if not match:
            warnings.warn('Unable to identify timestamp, using local time')
            dt = datetime.fromtimestamp(time())
        else:
            dt = datetime.strptime(match.group(0), r"%m/%d/%y %H:%M:%S")
        # Create list of measurements
        match = re.findall(r"([A-Z]+)\s+=\s+([-\d\.]+)", data_str)
        if not match:
            raise ValueError('{0} does not appear to contain any data'.format(data_str))
        else:
            measurements = []
            data = []
            for m in match:
                measurements.append(m[0])
                data.append(float(m[1]))
        # Check status
        match = re.search(r"([A-Z]+)\s*$", data_str)
        if not match:
            warnings.warn('Unable to identify status of measurement')
            status = 'UNKNOWN'
        else:
            status = match.group(1)
            if not status == 'SERVOLOCK':
                warnings.warn('Status is {0}, data may be inaccurate'.format(status))
        # Return
        return (dt, measurements, data, status)

    def get_data_immediate(self, return_raw=False):
        """ Polls the DewMaster for the current data on screen

        If the return_raw parameter is True, then this method returns the raw string sent by the
        DewMaster instead of processing the data first.

        If the return_raw parameter if False, then the data is returned as a 4-element tuple with
        the following structure:
            (time stamp, list of measurements, list of data values, measurement state)

        :param return_raw: If True, then the raw string is returned, otherwise the data is processed
        :type return_raw: bool
        :return: (time stamp, list of measurements, list of data values, measurement state)
        :rtype: (datetime.datetime, list of str, list of float, str)
        """
        # Write polling command and get data
        self.write('P')
        out = self.read()
        self.read()
        # Check if out captured 2 readings
        if re.search('\r\n', out):
            out = out.split('\r\n')[0]
        # Check that out has the proper number of values
        if return_raw:
            return out
        else:
            return self._parse_data(out)









