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

import warnings
import re
import os
from datetime import datetime
from time import time, sleep
import serial
import numpy as np

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
        # Parse port
        if type(port) not in [str, int]:
            try:
                port = int(port)
            except:
                raise TypeError('port should be an int or a str')
        if type(port) is int:
            port = 'COM{0}'.format(port)
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

    def flush(self):
        """ Reads any data in the output buffer without raising a warning if there is none
        """
        if self.device.inWaiting():
            self.device.read(self.device.inWaiting())

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
        and prints a warning.  The returned data is formatted as a string and has been stripped of
        leading and trailing whitespace.

        :return: All data waiting in the output buffer of the DewMaster
        :rtype: str
        """
        # Get start time and define stop time
        t_now = time()
        t_stop = t_now + self.device.timeout
        last_val = 0
        out = ''.encode(encoding='utf-8')
        while t_now < t_stop:
            now_val = self.device.inWaiting()
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
        self.flush()
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

        :param avg_num: The number of readings internally averaged for each output, between 1 and 16
        :type avg_num: int
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
        self.flush()
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
        self.flush()
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
        match = re.search(r"(([A-Z]+)\s*)+$", data_str)
        if not match:
            warnings.warn('Unable to identify status of measurement')
            status = 'UNKNOWN'
        else:
            status = match.group(0)
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
        self.flush()
        self.write('P')
        out = self.read()
        self.read()
        # Check that out has the proper number of values
        if return_raw:
            return out
        else:
            return self._parse_data(out)

    def log_data(self, filename, interval, total=None, npy=True, csv=True):
        """ Logs data to npy and csv files

        This routine logs data to either a numpy .npy file or a .csv file, or both.  The interval
        between data points is specified by interval, and should be a number in seconds.  The
        total amount of time is specified by total, and should be a number in seconds.  If total
        is left as None, then the log records until ctrl-c is pressed or the python session is
        closed.

        If both npy and csv are False, then the data will simply be printed to the screen.

        :param filename: The filename (without extensions) of the files which will be created
        :param interval: The time period in seconds between each data point
        :param totol: The total amount of time to record for, records forever if None
        :param npy: Specifies whether or not the data should be saved as an .npy file
        :param csv: Specifies whether or not the data should be saved as a .csv file
        :type filename: str
        :type interval: int
        :type total: int
        :type npy: bool
        :type csv: bool
        """
        # Check path and create filenames
        if not os.path.exists(os.path.split(filename)[0]):
            raise NotADirectoryError('filename does not point to a valid directory')
        csv_flnm = os.path.splitext(filename)[0] + '.csv'
        npy_flnm = os.path.splitext(filename)[0] + '.npy'
        # Start the data output from the DewMaster
        self.set_output_interval(interval)
        # Get the first data points
        data, tries = [], 0
        while not data:
            sleep(interval)
            raw_data = self.read().split('\r\n')
            for d in raw_data:
                try:
                    data.append(self._parse_data(d))
                    print(d)
                except ValueError:
                    pass
            if tries > 2:
                raise IOError('unable to get data from instrument')
            tries += 1
        # Start the files
        if npy:
            np.save(npy_flnm, data)
        if csv:
            with open(csv_flnm, mode='w') as f:
                # Write header
                f.write('Time, ')
                for measurement in data[0][1]:
                    f.write(measurement + ', ')
                f.write('Status\n')
                # Write data
                for d in data:
                    f.write(d[0].strftime('%m/%d/%Y %H:%M:%S') + ', ')
                    for measurement in d[2]:
                        f.write('{0:g}, '.format(measurement))
                    f.write(d[3] + '\n')
        for d in data:
            print(d)
        # Start the data collection loop
        if total is None:
            go_cond = True
        else:
            t_stop = time() + total
            go_cond = True
        while go_cond:
            data_n = []
            sleep(interval)
            raw_data = self.read().split('\r\n')
            for d in raw_data:
                try:
                    data_n.append(self._parse_data(d))
                    print(d)
                except ValueError:
                    pass
            # Write data to files
            if data_n:
                tries = 0
                # npy file
                data += data_n
                if npy:
                    np.save(npy_flnm, data)
                # csv file
                if csv:
                    with open(csv_flnm, mode='a') as f:
                        # Write data
                        for d in data_n:
                            f.write(d[0].strftime('%m/%d/%Y %H:%M:%S') + ', ')
                            for measurement in d[2]:
                                f.write('{0:g}, '.format(measurement))
                            f.write(d[3] + '\n')
            else:
                if tries > 3:
                    raise IOError('No data received for 4 tries in a row')
                tries += 1
            if total is not None:
                go_cond = time() < t_stop

class DewMasterData:
    """ A class for accessing data stored by the `log_data` method of the DewMaster class

    Note that the class uses the npy file saved by the log, and not the csv file.  If a filename
    with a csv extension is passed to the constructor, then it changes the extension to .npy and
    tries to import that file.

    """
    def __init__(self, filename):
        """ The constructor for the DewMasterData class

        :param filename: The complete path to the file
        :type filename: str
        """
        # Check extension
        if not os.path.splitext(filename)[1] == '.npy':
            warnings.warn('filename should point to an npy file')
            filename = os.path.splitext(filename)[0] +'.npy'
        # Try to import
        try:
            data = np.load(filename)
        except FileNotFoundError:
            raise FileNotFoundError('Can not locate file: {0}'.format(filename))
        # Assign data to self
        self.data = data

    ###############################################################################################
    # Internal Get Methods
    ###############################################################################################
    def _get_data(self):
        """ Returns the measured value for each of the three measurements at each data point

        The data is returned as a N x 3 numpy array with numeric entries

        :return: Measurement value for each of the three measurements at each data point
        :rtype: np.ndarray of float
        """
        return np.array(self.data[:, 2].tolist())

    def _get_datetimes(self):
        """ Returns the datetime instances as a single column ndarray

        :return: The datetime instances of each data point as a single column ndarray
        :rtype: np.ndarray of datetime.datetime
        """
        return self.data[:, 0]

    def _get_measurement_types(self):
        """ Returns the type for each of the three measurements for each data point

        The data is returned as a N x 3 numpy array with string entries

        :return: Type of each of the three measurements for each data point
        :rtype: np.ndarray of str
        """
        return np.array(self.data[:, 1].tolist())

    def _get_measurement_status(self):
        """ Returns the status of each measurement as a single column ndarray

        :return: The status of each measurement as a single column ndarray
        :rtype: np.ndarray of str
        """
        return self.data[:, 3]

    ###############################################################################################
    # User Get Methods
    ###############################################################################################
    def get_data(self):
        """ Returns the measured value for each of the three measurements at each data point

        The data is returned as a N x 3 numpy array with numeric entries

        :return: Measurement value for each of the three measurements at each data point
        :rtype: np.ndarray of float
        """
        return self._get_data()

    def get_measurement_types(self, summary=True):
        """ Returns the measurement type of the three measurements

        If summary is True, then this method returns a 3-element list with the type of each
        measurement.  If summary is False, then it returns an N x 3 numpy array with the type of
        measurement at every single data point.

        :param summary: If True, then a summary is returned otherwise, the type at each point is returned
        :type summary: bool
        :return: A 3-element list or an N x 3 ndarray describing the type of each of the three measurements
        :rtype: list or np.ndarray
        """
        types = self._get_measurement_types()
        if summary:
            return ['/'.join([x for x in set(types[:, j])]) for j in range(3)]
        else:
            return types

    def get_measurement_status(self, numerical=True):
        """ Returns the status of each measurement

        If numerical is True, then a numerical representation of the status is returned in which
          - 1 is for `'SERVOLOCK'`
          - 2 is for `'HOLD'`
          - 0 is for everything else

        If numerical is False, then the status of each point is returned as a string.

        :param numerical: If True, then a numerical representation of the status is returned
        :type numerical: bool
        :return: A numpy array with the status of each measurement
        :rtype: np.ndarray
        """
        status = self._get_measurement_status()
        if numerical:
            return np.array([1 if 'SERVOLOCK' in x else 2 if 'HOLD' in x else 0 for x in status])
        else:
            return status

    def get_times_in_seconds(self):
        """ Returns the time of each measurement in seconds since the epoch

        The epoch is defined in the python time module to be midnight of January 1st, 1970.  In
        other words, this method returns the time of each measurement in the same units as calling
        the internal python routine `time.time()`

        :return: A single column numpy array with the time of each data point in seconds
        :rtype: np.ndarray of float
        """
        return np.array([x.timestamp() for x in self._get_datetimes()])
