""" A package for accessing Tektronix oscilloscopes

This package relies primarily on the pyvisa package for communication with the
oscilloscope.

Note that the computer must have an visa installation (such as NI-Visa) in order
for pyvisa to be able to communicate with the oscilloscope.
"""

from time import sleep, time
import logging
import numpy as np
import visa

__author__ = "Chris Mueller"
__email__ = "chrisark7@gmail.com"
__status__ = "Development"

logger = logging.getLogger(__name__)


class Scope(object):
    """ A class for interacting with Tektronix oscilloscopes.

    Note that this class relies heavily on the pyvisa package.  It can be considered, in some
    sense, as a higher-level version of that package.

    Valid commands can be found in the TEK-XXXX-Series-programing-manual available from the
    Tektronix website.
    """
    def __init__(self, device_id=0, timeout=20):
        """ Initializes an instance of the Scope class.

        This function searches the devices connected to the computer and initializes the Scope
        object with one of them.  Note that it is still necessary to open the connection before
        being able to interact with the scope.

        The list of devices connected to the computer will be printed to the log.

        :param device_id: Integer or string which describes the device to connect to
        :param timeout: The default timeout value to use when interacting with the scope in seconds
        :type device_id: int or str
        :type timeout: int or float
        :return: An instance of the Scope class
        :rtype: Scope
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
                scope_id = device_id
        elif type(device_id) is not int:
            try:
                device_id = int(device_id)
            except:
                raise ValueError('device_id should be a string or an integer')
            if device_id > len(devices) - 1:
                raise ValueError('device_id is larger than the number of devices')
            else:
                scope_id = devices[device_id]
        elif device_id > len(devices) - 1:
            raise ValueError('device_id is larger than the number of devices')
        else:
            scope_id = devices[device_id]
        # Print chosen device
        logger.info('Initializing device: {0}'.format(scope_id))
        # Set parameters
        self.timeout = timeout*1e3
        self.scope_id = scope_id
        self.resource_manager = rm
        self.is_open = False
        self.device = None
        self.device_type = None
        self.measure_type = None

    ###############################################################################################
    # Low level commands
    ###############################################################################################
    def open(self):
        """ Opens the connection to the scope
        """
        if self.is_open:
            raise IOError('Comunication to scope is already open')
        try:
            self.device = self.resource_manager.open_resource(self.scope_id, open_timeout=10e3)
        except:
            raise IOError('Unable to open connection to scope.')
        # Determine device type
        self.is_open = True
        idstr = self.query('*IDN?')
        if not idstr:
            cnt = 0
            while not idstr and cnt < 5:
                sleep(5)
                idstr = self.query('*IDN?')
                cnt += 1
        logger.info('Successfully opened communication to device: {0}'.format(idstr))
        model = idstr.split(',')[1]
        if 'DPO' in model:
            self.device_type = 'DPO'
        elif 'TDS' in model:
            self.device_type = 'TDS'
        else:
            logger.error('Device type was not determined, assuming TDS')
            self.device_type = 'TDS'
        self.device.timeout = self.timeout

    def close(self):
        """ Closes the connection to the scope
        """
        if not self.is_open:
            raise IOError('Communication to scope is already closed')
        self.device.close()
        self.is_open = False

    def flush(self):
        """ Flushes the input and output buffers
        """
        if not self.is_open:
            raise IOError('Communication to scope is closed')
        self.device.flush(mask=64)
        self.device.flush(mask=128)

    def write(self, command):
        """ Writes a command to the scope

        :param command: A valid command to the scope
        :type command: str
        :return: the output of the write command
        :rtype: str
        """
        if not self.is_open:
            raise IOError('Communication to scope is closed')
        try:
            sleep(0.1)
            out = self.device.write(command)
        except visa.VisaIOError:
            raise ValueError('command {0} timed out; most likely it is not a valid command'.format(command))
        return out

    def read(self, timeout=0.5):
        """ Reads the most recent output from the scope
        
        The timeout argument is only used for USB devices which don't support the 
        bytes_in_buffer property.

        :param timeout: The timeout length in seconds
        :type timeout: float
        :return: The output of the read command
        :rtype: str
        """
        if not self.is_open:
            raise IOError('Communication to scope is closed')
        if self.device_type == 'TDS' or hasattr(self.device, 'bytes_in_buffer'):
            t0, tn = time(), 0
            self.device.timeout = timeout
            while (not self.device.bytes_in_buffer) and (tn < 5):
                sleep(0.1)
                tn = time() - t0
            else:
                sleep(0.1)
                try:
                    out = self.device.read()
                    self.device.timeout = self.timeout
                except visa.VisaIOError:
                    self.device.timeout = self.timeout
                    out = ''
                    logger.debug('Device did not return anything when trying to read')
        else:
            self.device.timeout = timeout
            try:
                out = self.device.read()
            except visa.VisaIOError:
                out = ''
                logger.debug('Device did not return anything when trying to read')
            self.device.timeout = self.timeout
        return out.rstrip()

    def query(self, command):
        """ Queries a value from the scope

        This method is equivalent to writing a query command and then reading the scope's output.

        :param command: A valid command to the scope
        :type command: str
        :return: the output of the query command
        :rtype: str
        """
        if not self.is_open:
            raise IOError('Communication to scope is closed')
        self.write(command)
        out = self.read()
        return out

    def set(self, command, value):
        """ Sets a value to the scope

        This method really just joins the command and value to make life easier on the user.

        :param command: A valid Tektronix command string
        :param value: The value to set
        :type command: str
        :type value: str or float or int
        """
        # Build the full command
        if type(value) is str:
            command_full = command + ' ' + value
        elif type(value) is int:
            command_full = command + ' {0}'.format(value)
        elif type(value) is float:
            command_full = command + ' {0}'.format(value)
        else:
            try:
                command_full = command + ' {0}'.format(value)
            except:
                raise ValueError('value appears to be a type which cannot be parsed')
        # Issue command_full
        self.write(command_full)

    def parse_channel(self, channel):
        """ A helper method for parsing the channel passed to many functions
        """
        # Set the channel
        if type(channel) is str:
            if channel.upper() not in ['CH1', 'CH2', 'CH3', 'CH4', 'REF1', 'REF2', 'REF3', 'REF4', 'MATH', 'MATH1']:
                logger.error('Channel was specified as an improper string')
                raise TypeError('Channel does not appear to be valid')
            else:
                ch_int = channel
        else:
            try:
                val = int(channel)
            except ValueError:
                logger.error('Channel is not a string but cannot be converted to an int')
                raise
            if val < 1 or val > 4:
                raise ValueError('Channel should be 1, 2, 3, or 4')
            else:
                ch_int = 'CH{0}'.format(val)
        return ch_int

    def set_measure_type(self, channel, measurement):
        """ Sets up the immediate measurement of the oscilloscope.

        This method is intended largely as a helper routine to the `measure` and `measure_*`
        methods.  It sets the channel and measurement type of the immediate measurement in the
        oscilloscope using the following commands:
            * MEASUREMENT:IMMED:SOURCE
            * MEASUREMENT:IMMED:TYPE

        The previous setting is stored in the object parameter `measure_type` so that it can be
        checked in the future.  This saves a significant number of writes to the scope when the
        same measurement is being called repeatedly.

        Valid values for channel can be (depending on scope model):
            1, 2, 3, 4, 'CH1', 'CH2', 'CH3', 'CH4', 'MATH', 'REF1', 'REF2', 'REF3', 'REF4'

        Valid values for the measurement can be (depending on scope model):
            AMPlitude, AREa, BURst, CARea, CMEan, CRMs, DELAY, FALL, FREQuency, HIGH, LOW, MAXimum,
            MEAN, MINImum, NDUty, NOVershoot, NWIdth, PDUty, PERIod, PHASE, PK2pk, POVershoot,
            PWIdth, RISe, RMS

        :param channel: An integer which is a valid channel number or the channel name
        :param measurement: A string which specifies a valid measurement for the given channel
        :type channel: str or int
        :type measurement: str
        :return: (value, unit, error code)
        :rtype: (float, str, int)
        """
        logger.debug('set_measure_type(channel={0}, measurement={1})'.format(channel, measurement))
        # Parse channel
        ch_int = self.parse_channel(channel=channel)
        # Check if the parameters need to be set
        set_flag = False
        if self.measure_type is None:
            set_flag = True
        elif not ch_int == self.measure_type[0]:
            set_flag = True
        elif not measurement.upper in self.measure_type[1]:
            set_flag = True
        # Set the measurment if need be
        if set_flag:
            logger.debug('Setting measurement channel/type to: {0}/{1}'.format(
                ch_int, measurement))
            # Set the measurement
            self.write('MEASUREMENT:IMMED:SOURCE ' + ch_int)
            self.write('MEASUREMENT:IMMED:TYPE ' + measurement.upper())
            # Check if the set measurement type was the same as the previous
            out = self.query('MEASUREMENT:IMMED:TYPE?')
            logger.debug('Measurement:  Requested: ' + measurement + '  Actual: ' + out)
            if self.measure_type is None:
                self.measure_type = [ch_int, [measurement.upper()], out]
            elif out == self.measure_type[2]:
                self.measure_type[1].append(measurement.upper())
            else:
                self.measure_type = [ch_int, [measurement.upper()], out]
        else:
            logger.debug('Measurement was already set to channel/type: {0}/{1}'.format(
                self.measure_type[0], self.measure_type[2]))

    ###############################################################################################
    # Position the Waveform
    ###############################################################################################
    def autoscale_y(self, channel=1):
        """ Adjusts the scale and position of the waveform to use approximately 3/4 of the screen

        :param channel: A channel number or string
        :type channel: int
        """
        logger.debug('autoscale_y(channel={0})'.format(channel))
        # Set the channel
        ch_int = self.parse_channel(channel=channel)
        # Initialize position to zero
        self.write(ch_int + ':POSITION 0')
        is_good = False
        cnt = 0
        while (not is_good) and cnt < 15:
            # Measure min and max of waveform
            wfmin = self.measure(channel=ch_int, measurement='MINIMUM')[0]
            wfmax = self.measure(channel=ch_int, measurement='MAXIMUM')[0]
            # Measure min and max of screen
            scscale = float(self.query(ch_int + ':SCALE?'))
            scpos = float(self.query(ch_int + ':POSITION?'))
            scmin = (-4 - scpos) * scscale
            scmax = (4 - scpos) * scscale
            scdif = scmax - scmin
            # Too large?
            if wfmax > scmax - scdif/8:
                newscale = scscale*1.5
                self.write(ch_int + ':SCALE {0:0.1e}'.format(newscale))
            elif wfmin < scmin + scdif/8:
                newscale = scscale*1.5
                self.write(ch_int + ':SCALE {0:0.1e}'.format(newscale))
            # Centered?
            elif abs(scmax - wfmax - abs(scmin - wfmin)) > 0.1 * scdif:
                newpos = (scmax - wfmax - abs(scmin - wfmin))/(2*scscale) + scpos
                self.write(ch_int + ':POSITION {0:0.1e}'.format(newpos))
            # Too small?
            elif wfmax - wfmin < scdif/2:
                newscale = scscale * 0.9
                self.write(ch_int + ':SCALE {0:0.1e}'.format(newscale))
            else:
                is_good = True
            cnt += 1

    def center_y(self, channel=1):
        """ Centers the waveform in the y direction

        This method centers the waveform by measuring the min and max and setting the center
        position to balance the min and max on-screen.

        Note that this method will not recognize the min or max properly if they are off screen.

        :param channel: A channel number or string
        :type channel: int
        """
        logger.debug('center_y(channel={0})'.format(channel))
        # Set the channel
        ch_int = self.parse_channel(channel=channel)
        # Measure min and max of waveform
        wfmin = self.measure(channel=ch_int, measurement='MINIMUM')[0]
        wfmax = self.measure(channel=ch_int, measurement='MAXIMUM')[0]
        # Measure min and max of screen
        scscale = float(self.query(ch_int + ':SCALE?'))
        scpos = float(self.query(ch_int + ':POSITION?'))
        scmin = (-4 - scpos) * scscale
        scmax = (4 - scpos) * scscale
        # Write new position to scope
        newpos = (scmax - wfmax - abs(scmin - wfmin))/(2*scscale) + scpos
        self.write(ch_int + ':POSITION {0:0.1e}'.format(newpos))

    def set_trigger_to_50_percent(self):
        """ This is a simple command to set the trigger level to 50%.

        This command is equivalend to pushing the front panel button.  Note that the process of
        setting the trigger level to 50% takes a few seconds during which the scope will not
        repsond to commands so it may be necessary to sleep before issuing new commands in a
        script.
        """
        logger.debug('trigger_to_50_percent()')
        if self.device_type == 'TDS':
            self.write('TRIGGER:A:SETLEVEL')
        else:
            self.write('TRIGGER:A SETLEVEL')

    ###############################################################################################
    # Get Information about the Waveform
    ###############################################################################################
    def get_data(self, channel=1, data_width=1, data_units='volts'):
        """ Retrieves the current data for the given channel.

        Note that the time to retrieve the data can be quite long, up to ~2 minutes.

        Valid channels may include (different for different scopes):
            1, 2, 3, 4, 'CH1', 'CH2', 'CH3', 'CH4', 'MATH', 'REF1', 'REF2', 'REF3', 'REF4'

        :param channel: An integer which is a valid channel number or the channel name
        :param data_width: Sets the bit depth of the returned data (1=8 bit, 2=16bit)
        :param data_units: 'volts' returns the data in volts and 'bytes' returns the data in the form transmitted by the scope
        :type data_width: int
        :type channel: int or str
        :type data_units: str ('volts' or 'bytes')
        :return: The data as a numpy array for the channel
        :rtype: np.ndarray, np.ndarray
        """
        logger.debug('get_data(channel={0}, data_width={1}, data_units={2}'.format(
            channel, data_width, data_units))
        # Set the channel
        ch_int = self.parse_channel(channel)
        out = self.write('DATA:SOURCE ' + ch_int)
        # Set the data width
        if data_width not in [1, 2]:
            logger.warn('data_width should be 1 or 2, defaulting to 1.')
            data_width = 1
        # Check that the data is ready to be collected
        if self.device_type == 'TDS':
            wfmpre = self.device.query('WFMPRE?')
        else:
            wfmpre = self.device.query('WFMOUTPRE?')
        if len(wfmpre.split(';')) < 8:
            logger.error('Data does not appear to be ready')
            raise IOError('Data is not ready to be collected, make sure it is displayed on the screen.')
        # Set the scope output type
        self.write('DATA:ENCDG ASCII')
        self.write('DATA:START 1')
        self.write('DATA:STOP 1000000')
        # Set data bit width
        if self.device_type == 'TDS':
            out = self.write('DATA:WIDTH {0}'.format(data_width))
        else:
            self.write('WFMOUTPRE:BYT_NR {0}'.format(data_width))
        # Increase the timeout to 5 minutes
        timeout_temp = 5*60*1e3
        # Retrieve data
        logger.info('Retrieving data')
        self.write('*WAI')
        self.write('CURVE?')
        try:
            data_raw = self.read(timeout=timeout_temp).split(' ')[-1]
        except visa.VisaIOError:
            self.device.timeout = self.timeout
            logger.error('Data retrieval timed out.')
            raise IOError('Data retrieval timed out.')
        logger.info('Data retrieval finished')
        # Reset the timeout
        self.device.timeout = self.timeout
        # Get the scope parameters to convert the data units
        sleep(2)
        logger.debug('Getting info to convert units of scope trace')
        if self.device_type == 'TDS':
            pre = 'WFMPRE:'
        else:
            pre = 'WFMOUTPRE:'
        xincr = float(self.query(pre + 'XINCR?').split(' ')[-1])
        if not data_units == 'bytes':
            ymult = float(self.query(pre + 'YMULT?').split(' ')[-1])
            yzero = float(self.query(pre + 'YZERO?').split(' ')[-1])
            yoff = float(self.query(pre + 'YOFF?').split(' ')[-1])
            data = (np.array([float(x) for x in data_raw.split(sep=',')]) - yoff) * ymult + yzero
        else:
            data = np.array([float(x) for x in data_raw.split(sep=',')])
        times = np.arange(0, xincr * len(data), xincr)
        return times, data

    def measure(self, channel=1, measurement='amplitude'):
        """ Returns the value of a specified measurement on the specified channel

        Valid values for channel can be (depending on scope model):
            1, 2, 3, 4, 'CH1', 'CH2', 'CH3', 'CH4', 'MATH', 'REF1', 'REF2', 'REF3', 'REF4'

        Valid values for the measurement can be (depending on scope model):
            AMPlitude, AREa, BURst, CARea, CMEan, CRMs, DELAY, FALL, FREQuency, HIGH, LOW, MAXimum,
            MEAN, MINImum, NDUty, NOVershoot, NWIdth, PDUty, PERIod, PHASE, PK2pk, POVershoot,
            PWIdth, RISe, RMS

        :param channel: An integer which is a valid channel number or the channel name
        :param measurement: A string which specifies a valid measurement for the given channel
        :type channel: str or int
        :type measurement: str
        :return: (value, unit, error code)
        :rtype: (float, str, int)
        """
        logger.debug('measure(channel={0}, measurement={1}'.format(channel, measurement))
        # Set the measure type
        self.set_measure_type(channel=channel, measurement=measurement)
        # Make the measurement
        measurement_made, cnt = False, 0
        while not measurement_made:
            # Try to get the measurement value
            if self.device_type == 'TDS':
                data = self.query('MEASUREMENT:IMMED:DATA?')
            else:
                data = self.query('MEASUREMENT:IMMED:VALUE?')
            # Check if the returned value is empty
            if data:
                measurement_made = True
            # If the measurement has been tried 10 times then raise an error
            elif cnt > 9:
                logger.error('Measurement did not return a result for 10 tries')
                raise ValueError('Measurement did not return a result for 10 tries')
            else:
                cnt += 1
                sleep(1)
        # Process data
        if self.device_type == 'TDS':
            data = data.split(',')
            value, error = float(data[0]), int(data[1])
        else:
            # We assign an error value of None to the DPO series oscilliscopes because they don't return the error
            value, error = float(data), None
        unit = self.query('MEASUREMENT:IMMED:UNITS?').replace('"', '')
        if not (error == 0 or error is None):
            logger.warn('Measurement returned error code {0}'.format(data[1]))
        return value, unit, error

    def measure_many(self, channel=1, measurement='PWIDTH', num_measurements=16):
        """ Makes numerous successive measurements in order to collect some statistical info

        Valid values for channel can be (depending on scope model):
            1, 2, 3, 4, 'CH1', 'CH2', 'CH3', 'CH4', 'MATH', 'REF1', 'REF2', 'REF3', 'REF4'

        Valid values for the measurement can be (depending on scope model):
            AMPlitude, AREa, BURst, CARea, CMEan, CRMs, DELAY, FALL, FREQuency, HIGH, LOW, MAXimum,
            MEAN, MINImum, NDUty, NOVershoot, NWIdth, PDUty, PERIod, PHASE, PK2pk, POVershoot,
            PWIdth, RISe, RMS

        :param channel: An integer which is a valid channel number or the channel name
        :param measurement: A string which specifies a valid measurement for the given channel
        :param num_measurements: The number of successive measurements to make
        :type channel: str or int
        :type measurement: str
        :type num_measurements: int
        :return: (value, unit, error code)
        :rtype: list of float
        """
        logger.debug('measure_many(channel={0}, measurement={1}, num_measurements={2}'.format(
            channel, measurement, num_measurements))
        # Set the measurement parameters
        self.set_measure_type(channel=channel, measurement=measurement)
        # Make the measurements
        data = []
        for _ in range(num_measurements):
            measurement_made, cnt = False, 0
            while not measurement_made:
                # Make the measurement
                out = self.query('MEASUREMENT:IMMED:VALUE?')
                # Check if the returned value is not empty
                if out:
                    measurement_made = True
                # If the measurement has been tried 10 times then raise an error
                elif cnt > 9:
                    logger.error('Measurement did not return a result for 10 tries')
                    raise ValueError('Measurement did not return a result for 10 tries')
                else:
                    cnt += 1
                    sleep(1)
            data.append(float(out))
        return data

    def measure_pulsewidth(self, channel=1, num_measurements=16):
        """ Measures the pulsewidth with statistics

        This method measures the pulsewidth numerous times consecutively and returns both the
        mean and standard deviation of those measurements.  It is preferred to setting up your own
        loop via the ``measure`` method because it only goes through the initial setup once.

        :param num_measurements: The number of measurements to collect for statistics
        :type num_measurements: int
        :return: (mean, standard deviation)
        :rtype: (float, float)
        """
        logger.debug('measure_pulsewidth(channel={0}, num_measurements={1}'.format(channel, num_measurements))
        data = self.measure_many(channel=channel, measurement='PWIDTH',
                                 num_measurements=num_measurements)
        # Calculate statistics
        avg, std = float(np.mean(data)), float(np.std(data))
        if std/avg > 0.2:
            logger.warn('Pulsewidth standard deviation is greater than 20%')
        # Return
        return avg, std

    ###############################################################################################
    # Record/Set Instrument State
    ###############################################################################################
    def get_state(self, channel=1):
        """ Records the on-screen settings for a particular channel.

        Unlike the get_data() and measure() methods, this method only works on the devices active
        channels.  I.E. not on the math or reference channels.

        Valid values of channel can be (depending on scope model):
            1, 2, 3, 4, 'CH1', 'CH2', 'CH3', 'CH4'

        :param channel: integer or string describing the channel
        :type channel: int or str
        :return: a dictionary containing all of the parameters describing the current state of the channel
        :rtype: dict
        """
        logger.debug('get_state(channel={0})'.format(channel))
        # Set the channel
        ch_int = self.parse_channel(channel=channel)
        # Define the dictionary
        state = {ch_int + ':BANDWIDTH': None,
                 ch_int + ':COUPLING': None,
                 ch_int + ':DESKEW': None,
                 ch_int + ':IMPEDANCE': None,
                 ch_int + ':INVERT': None,
                 ch_int + ':OFFSET': None,
                 ch_int + ':POSITION': None,
                 ch_int + ':PROBE': None,
                 ch_int + ':SCALE': None,
                 ch_int + ':YUNIT': None,
                 'HORIZONTAL:DELAY:STATE': None,
                 'HORIZONTAL:DELAY:TIME': None,
                 'HORIZONTAL:MAIN:SCALE': None,
                 'HORIZONTAL:MAIN:SECDIV': None,
                 'HORIZONTAL:RECORDLENGTH': None,
                 'HORIZONTAL:RESOLUTION': None,
                 'HORIZONTAL:TRIGGER:POSITION': None,
                 'TRIGGER:A:TYPE': None,
                 'TRIGGER:A:LEVEL': None,
                 'TRIGGER:A:HOLDOFF:TIME': None,
                 'TRIGGER:A:HOLDOFF:VALUE': None,
                 'TRIGGER:A:EDGE:COUPLING': None,
                 'TRIGGER:A:EDGE:SLOPE': None,
                 'TRIGGER:A:EDGE:SOURCE': None}
        # Query the values
        for key in state:
            state[key] = self.query(key + '?')
        # Return
        return state

    def set_state(self, state):
        """ Sets the state of the scope using the parameters contained in the state dictionary

        The dictionary containing the scope's parameters is rather complex because the key's of
        the dictionary are the commands issued to the scope.  The easiest way to see an example
        is to run the get_state() method.

        :param state: a dictionary containing the parameters defining the scope's state
        :type state: dict
        """
        logger.debug('set_state({0})'.format(state))
        # Check type of state
        if type(state) is not dict:
            raise TypeError('state should be a dictionary')
        # Set parameters
        for key in state:
            self.write(key + ' ' + state[key])
            # Check if it was set
            out = self.query(key + '?')
            if not out == state[key]:
                logger.warn(key + ' was not set properly. Value is ' + out + ' while ' +
                              state[key] + ' was requested.')











