"""
This is a package for connecting to Ophir power meters.  It is addapted from Daniel Dietze's
package whose original header statement is included below.  Many of the changes are simply updating
to Python 3.

# Copyright (C) 2010-2013 Daniel Dietze
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""

# modules
import win32com.client
from time import sleep
import logging
from collections import Counter

__email__ = "chrisark7@gmail.com"
__status__ = "Development"

logger = logging.getLogger(__name__)

# class
class OphirCOM(object):
    """    Python interface to the Ophir USBI device.

    A class object contains the following attributes
      - USBI_handle: The handle returned when the device is initialized
      - USBI_channel: The channel to act on
      - timeout: A timeout value for measurements
      - device_ready: A boolean to keep track of whether communication is open yet
      - Plus others (see below)
    """
    def __init__(self):
        """ Initialize communication through ActiveX

        Note that the device is not chosen and direct communication is not yet opened during
        this initialization.  The connect() method must be run afterward to open communication to
        the device.

        :return: An instance of the OphirCOM class
        :rtype: OphirCOM
        """
        # Initialize values
        self.USBI_handle = 0
        self.USBI_channel = 0
        self.timeout = 0.1
        self.device_ready = False
        self.measurement_mode = 0
        self.MM_Modes = ()
        self.range = 0
        self.MM_Ranges = ()
        self.wavelength = 0
        self.MM_Wavelengths = ()
        self.measurement_running = False
        # Connect to activeX class and store module in adwin_ax
        logger.info("Try to connect to ActiveX component..")
        self.USBI_com = win32com.client.Dispatch("OphirLMMeasurement.CoLMMeasurement")
        logger.info("..success")
        logger.info("COM Version: {0}".format(self.USBI_com.GetVersion()))

    def __del__(self):
        # Clean up
        logger.debug('__del__')
        self.disconnect()
        del self

    def scanUSB(self):
        """ Returns a list of attached USB Devices

        :return: list of attached USB devices
        :rtype: tuple of str
        """
        logger.debug('scanUSB()')
        return self.USBI_com.ScanUSB()

    def connect(self, devID=0):
        """ Establishes a connection to the device specified by devID

        The devID is the position in the tuple returned by the scanUSB() method.

        :param devID: The device number to connect to
        :type devID: int
        """
        logger.debug('connect(devID={0})'.format(devID))
        # Iterate all connected USB sensors
        devices = self.scanUSB()
        logger.info("Found {0} USB Devices..".format(len(devices)))
        # Check devID
        if type(devID) is not int:
            try:
                devID = int(devID)
            except:
                raise TypeError('devID should be an integer')
        if devID > len(devices) - 1:
            raise ValueError('devID is larger than the number of devices')
        # Connect
        self.USBI_handle = self.USBI_com.OpenUSBDevice(devices[devID])
        logger.info("Connected to Sensor {0}".format(
              self.USBI_com.GetSensorInfo(self.USBI_handle, self.USBI_channel)))
        # Read device state
        try:
            self.measurement_mode, self.MM_Modes = self.USBI_com.GetMeasurementMode(self.USBI_handle, self.USBI_channel)
            self.range, self.MM_Ranges = self.USBI_com.GetRanges(self.USBI_handle, self.USBI_channel)
            self.wavelength, self.MM_Wavelengths = self.USBI_com.GetWavelengths(self.USBI_handle, self.USBI_channel)
        except:
            pass

    def disconnect(self):
        """ Closes the connection to the power meter
        """
        logger.debug('disconnect()')
        # Close connection
        if not self.USBI_handle == 0:
            self.USBI_com.Close(self.USBI_handle)
            self.USBI_handle = 0
            logger.info('Disconnected from device')
        else:
            logger.info('Device is not connected')

    def reset(self):
        """ Resets the device using the internal reset command
        """
        logger.debug('reset()')
        if not self.USBI_handle == 0:
            self.USBI_com.ResetDevice(self.USBI_handle)
        else:
            raise IOError('Device is not connected')

    ###############################################################################################
    # Get/set Methods
    ###############################################################################################
    def get_device_info(self):
        """ Returns the device info stored in the device

        :return: tuple containing (model, software version, serial number)
        :rtype: tuple of str and int
        """
        logger.debug('get_device_info()')
        return self.USBI_com.GetDeviceInfo(self.USBI_handle, self.USBI_channel)

    def get_measurement_mode(self):
        """ Returns the current measurement mode of the device

        This method returns an integer corresponding to the current measurement mode.  Look at the
        MM_Modes parameter to see the list of possible measurement modes

        :return: An integer corresponding to the measurement mode
        :rtype: int
        """
        logger.debug('get_measurement_mode()')
        return self.measurement_mode

    def set_measurement_mode(self, newmode):
        """ Sets the measurement mode of the device

        Refer to the MM_Modes property to see a list of possible modes.  The newmode parameter is
        an integer corresponding to this list

        :param newmode: An integer corresponding to a valid measurement mode
        :type newmode: int
        """
        logger.debug('set_measurement_mode(newmode={0})'.format(newmode))
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected')
        if newmode < 0 or newmode >= len(self.MM_Modes):
            raise ValueError('newmode should be an integer between 0 and {0}'.format(
                             len(self.MM_Modes)))
        self.measurement_mode = newmode
        self.USBI_com.SetMeasurementMode(self.USBI_handle, self.USBI_channel, newmode)

    def get_wavelength(self):
        """ Returns an integer corresponding to the current wavelength setting

        Refer to the MM_Wavelengths parameter for a list of possible wavelengths.

        :return: The current wavelength setting of the instrument
        :rtype: int
        """
        logger.debug('get_wavelength()')
        return self.wavelength

    def set_wavelength(self, newmode):
        """ Sets the instrument's operating wavelength

        Refer to the MM_Wavelengths for a list of possible wavelengths.  The newmode parameter
        should be an integer corresponding to this list.

        :param newmode: An integer corresponding to a valid wavelength setting
        :type newmode: int
        """
        logger.debug('set_wavelength(newmode={0})'.format(newmode))
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if newmode < 0 or newmode >= len(self.MM_Wavelengths):
            raise ValueError('newmode should be an integer between 0 and {0}'.format(
                             len(self.MM_Wavelengths)))
        self.wavelength = newmode
        self.USBI_com.SetWavelength(self.USBI_handle, self.USBI_channel, newmode)

    def get_range(self):
        """ Returns the current range setting of the device

        Refer to MM_Ranges to see a list of the possible ranges supported by the device.

        :return: An integer corresponding to the current range setting of the device.
        :rtype: int
        """
        logger.debug('get_range()')
        return self.range

    def set_range(self, newmode):
        """ Sets the range setting of the device

        Refer to MM_Ranges to see a list of the possible ranges supported by the device.  The
        newmode parameter should be an integer corresponding to this list.

        :param newmode: An integer corresponding to a valid range setting
        :type newmode: int
        """
        logger.debug('set_range(newmode={0})'.format(newmode))
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if newmode < 0 or newmode >= len(self.MM_Ranges):
            raise ValueError('newmode should be an integer between 0 and {0}'.format(
                             len(self.MM_Ranges)))
        self.range = newmode
        self.USBI_com.SetRange(self.USBI_handle, self.USBI_channel, newmode)

    ###############################################################################################
    # Set Measurement Type
    ###############################################################################################
    def set_turbo_mode(self, freq):
        """ Puts the device into turbo mode and sets the measurement frequency

        Turbo mode is used when the measurement frequency needs to be greater than 130 Hz.  In
        this mode, the data is collected on the device and is delivered to the computer every 50
        milliseconds.

        :param freq: A measurement frequency in Hz between 100 and 2000
        :type freq: float
        """
        logger.debug('set_turbo_mode(freq={0})'.format(freq))
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        # Turn off immediate mode
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 0)
        # Set the frequency of turbo mode
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 1, freq)
        # Turn on turbo mode
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 1)

    def set_immediate_mode(self):
        """ Sets the device to operate in immediate mode.

        In this mode, as opposed to turbo mode, the device reports the power measurements in
        real time.  This mode is capable of operating up to 130 Hz for Vega meters according to
        the manual.
        """
        logger.debug('set_immediate_mode()')
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        # Turn turbo mode off
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 0)
        # Turn immediate mode on
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 1)

    def set_standard_mode(self):
        """ Sets the device into the standard delivery mode
        """
        logger.debug('set_standard_mode()')
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        # Turn turbo mode off
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 0, 0)
        # Turn immediate mode off
        self.USBI_com.ConfigureStreamMode(self.USBI_handle, self.USBI_channel, 2, 0)

    ###############################################################################################
    # Get Data from Device
    ###############################################################################################
    def get_data_fixed(self, num_samples=None, time_length=None):
        """ Gets power data for a fixed amount of time or number of samples

        This function is used to retrieve data from the power meter.  It has two options for
        specifying the amount of data to get; length of time or number of samples.  If both are
        specified, then the number of samples will be used and the time will be ignored.

        :param num_samples: number of data points returned
        :param time: length of time in seconds to collect data (ignored if num_samples is specified)
        :type num_samples: int
        :type time: float
        :return: (power data, timestamps)
        :rtype: (list of float, list of float)
        """
        logger.debug('get_data_fixed(num_samples={0}, time_length={1})'.format(
            num_samples, time_length))
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if self.measurement_running:
            raise IOError('Measurement is already running')
        self.measurement_running = True
        try:
            # Define error code key
            errors = {0: 'OK', 1:'Overrange', 2:'Saturated', 3:'Missing', 4:'Reset State',
                      5:'Waiting', 6:'Summing', 7:'Timeout', 8:'Peak Over', 9:'Energy Over'}
            # Check types
            if num_samples is not None and type(num_samples) is not int:
                try:
                    num_samples = int(num_samples)
                except:
                    raise TypeError('num_samples should be an integer')
            if num_samples is None and time_length is None:
                raise ValueError('Either num_samples of time_length must be specified')
            # Collect data
            if num_samples is None: # Record for time_length
                # Get data
                self.USBI_com.StartStream(self.USBI_handle, self.USBI_channel)
                sleep(time_length + 0.1)
                self.USBI_com.StopStream(self.USBI_handle, self.USBI_channel)
                pows, times, stats = self.USBI_com.GetData(self.USBI_handle, self.USBI_channel)
                # Trim to desired time length
                if times[-1] - times[0] > time_length*1e3:
                    dt = [x - times[0] for x in times]
                    ind = [i for i, v in enumerate(dt) if v > time_length*1e3][0]
                    pows, times, stats = pows[0:ind], times[0:ind], stats[0:ind]
            else: # Record for num_samples
                pows, times, stats = [], [], []
                # Start stream
                self.USBI_com.StartStream(self.USBI_handle, self.USBI_channel)
                while len(pows) < num_samples:
                    sleep(0.05)
                    pows_n, times_n, stats_n = self.USBI_com.GetData(self.USBI_handle, self.USBI_channel)
                    pows.extend(pows_n)
                    times.extend(times_n)
                    stats.extend(stats_n)
                # Stop stream
                self.USBI_com.StopStream(self.USBI_handle, self.USBI_channel)
                # Trim data
                if len(pows) > num_samples:
                    i = num_samples
                    pows, times, stats = pows[0:i], times[0:i], stats[0:i]
            # Check the status of each point
            cnt = Counter(stats)
            if len(cnt.keys()) > 1:
                for jj in cnt:
                    if jj in errors:
                        logger.info('{0} elements with error code: {1}'.format(cnt[jj], errors[jj]))
                    else:
                        logger.info('{0} elements with unknown error code'.format(cnt[jj]))
        except:
            self.measurement_running = False
            raise
        # Return
        self.measurement_running = False
        times = tuple([jj*1e-3 for jj in times])
        return pows, times

    def start_data_stream(self):
        """ Starts the data stream from the power meter for continuous collection

        This method is used to initiate the data stream from the power meter.  It is necessary
        to run this function before calling the get_data_continuous() method.
        """
        logger.debug('start_data_stream()')
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if self.measurement_running:
            raise IOError('Measurement is already running')
        self.USBI_com.StartStream(self.USBI_handle, self.USBI_channel)
        self.measurement_running = True

    def stop_data_stream(self):
        """ Stops the data stream from the power meter for continuous collection

        This method is used to stop the data stream from the power meter.  It should be run once
        continuous data collection is over.
        """
        logger.debug('stop_data_stream')
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if not self.measurement_running:
            raise IOError('Measurement is not running')
        self.USBI_com.StopStream(self.USBI_handle, self.USBI_channel)
        self.measurement_running = False

    def get_data_continuous(self):
        """ Gets data from the power meter data stream.

        This method collects all of the data sent by the power meter since either 1) the stream
        was started or 2) get_data_continuous() was last called.

        :return: (power data, times)
        :rtype: (list of float, list of float)
        """
        logger.debug('get_data_continuous()')
        # Check if the device is connected
        if self.USBI_handle == 0:
            raise IOError('Device is not yet connected.')
        if not self.measurement_running:
            raise IOError('Measurement is not running')
        # Define error code key
        errors = {0: 'OK', 1:'Overrange', 2:'Saturated', 3:'Missing', 4:'Reset State',
                  5:'Waiting', 6:'Summing', 7:'Timeout', 8:'Peak Over', 9:'Energy Over'}
        # Get data
        pows, times, stats = self.USBI_com.GetData(self.USBI_handle, self.USBI_channel)
        # Check the status of each point
        cnt = Counter(stats)
        if len(cnt.keys()) > 1:
            for jj in cnt:
                if jj in errors:
                    logger.info('{0} elements with error code: {1}'.format(cnt[jj], errors[jj]))
                else:
                    logger.info('{0} elements with unknown error code'.format(cnt[jj]))
        # Return
        times = tuple([jj*1e-3 for jj in times])
        return pows, times
