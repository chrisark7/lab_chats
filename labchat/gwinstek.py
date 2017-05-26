""" A package for communicating with GW Instek function generators

This package was written primarily to communicate with the GW Instek AFG-2225,
but it should be generic enough to communicate with other function generator
products from GW Instek

The package relies on the pyvisa package for communication with the instrument
which, in turn, relies on an installation of the VISA protocal such as NIVISA
from National Instruments.
"""

import logging
from labchat.visausb import VisaUsbInstrument

__email__ = "chrisark7@gmail.com"
__status__ = "Development"

logger = logging.getLogger(__name__)


class AFG2225(VisaUsbInstrument):
    """ A class for communicating with the GW Instek AFG-2225

    This class is likely generic enough to work with other models in the GW
    Instek line but has not been tested.
    """
    def __init__(self, device_id=0, timeout=0.5):
        """ The constructor for the AFG2225 class

        This function searches the devices connected to the computer and
        initializes the AFG2225 instance with one of them.  Note that
        it is still necessary to open the connection before being able to
        interact with the instrument.

        The list of devices connected to the computer will be printed to the
        log.

        :param device_id: Integer or string which describes the device to connect to
        :param timeout: The timeout value to use with the instrument in seconds
        :type device_id: int or str
        :type timeout: int or float
        :return: An instance of the AFG2225 class
        :rtype: AFG2225
        """
        super(AFG2225, self).__init__(device_id=device_id, timeout=timeout)

    ###########################################################################
    # Helper Methods
    ###########################################################################
    @staticmethod
    def check_channel(channel):
        """ Checks to make sure that channel is an integer in [1, 2]

        :param channel: channel to check
        :type channel: int
        :return: channel integer in [1, 2]
        :rtype: int
        """
        try:
            channel = int(channel)
        except:
            raise TypeError("channel should be an integer")
        if channel not in [1, 2]:
            raise ValueError("channel should be 1 or 2")
        return channel

    ###########################################################################
    # Set/Get Waveform Properties Individually
    ###########################################################################
    def set_function(self, channel, function):
        """ Sets the channel's function

        Possible channel functions are: SINUSOID, SQUARE, RAMP, PULSE, NOISE,
        USER

        :param channel: The channel to set (1 or 2)
        :param function: A string corresponding to the function
        :type channel: int
        :type function: str
        """
        assert type(function) is str
        # Check channel
        channel = self.check_channel(channel)
        # Define possibilities
        long_strings = ["SINUSOID", "SQUARE", "RAMP", "PULSE", "NOISE", "USER"]
        short_strings = ["SIN", "SQU", "PULS", "NOIS"]
        # Check for string match
        function = function.upper()
        if function not in long_strings + short_strings:
            best_match = self.get_close_string(function, long_strings + short_strings)
            if best_match is None:
                raise ValueError("function does not match any possible functions")
            else:
                logger.warning("{0} does not match any function; using {1} "
                               "instead".format(function, best_match))
            function = best_match
        # Form command
        command = "SOUR{0}:FUNCTION {1}".format(channel, function)
        # Issue command
        self.write(command)

    def get_function(self, channel):
        """ Returns the channel's current function setting

        :param channel: The channel to query
        :type channel: int
        :return: The current function setting for the specified channel
        :rtype: str
        """
        # Check channel
        channel = self.check_channel(channel)
        # Get Current Function
        return self.query("SOURCE{0}:FUNCTION?".format(channel))

    def set_frequency(self, channel, frequency):
        """ Sets the channel's frequency

        The AG2225 can be set down to uHz even when the frequency is in the MHz
        regime.  So, 10.000000000001e6 will be set even though it is highly
        unlikely that the internal oscillator has this kind of precision.

        :param channel: The channel to adjust (1 or 2)
        :param frequency: The frequency in Hz
        :type channel: int
        :type frequeny: float or int
        :return:
        """
        # Check channel
        channel = self.check_channel(channel)
        # Check
        # Query the min and max possible frequencies
        min_freq = float(self.query("SOURCE{0}:FREQUENCY? MIN".format(channel)))
        max_freq = float(self.query("SOURCE{0}:FREQUENCY? MAX".format(channel)))
        # Check that frequency is in the range
        if frequency > max_freq:
            logger.warning("Frequency is greater than the max for this function; "
                           "setting to {0} instead".format(max_freq))
            self.write("SOURCE{0}:FREQUENCY MAX".format(channel))
        elif frequency < min_freq:
            logger.warning("Frequency is less than the min for this function; "
                           "setting to {0} instead".format(min_freq))
            self.write("SOURCE{0}:FREQUENCY MIN".format(channel))
        else:
            command = "SOURCE{0}:FREQUENCY {1}".format(channel, frequency)
            self.write(command)

    def get_frequency(self, channel):
        """ Returns the channel's current frequency in Hz

        :param channel: The channel to query
        :type channel: int
        :return: The channel's current frequency
        :rtpye: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Return
        return float(self.query("SOURCE{0}:FREQUENCY?".format(channel)))

    def set_amplitude(self, channel, amplitude):
        """ Sets the channel's amplitude

        Units are Vpp

        The min and max of the possible amplitude settings depend on the
        current function and output load settings on the function generator
        This method will warn you if the value is below the min or above the
        max and set the amplitude appropriately.

        :param channel: The channel who's amplitude will be set
        :param amplitude: The amplitude value to set in units given by `unit`
        :type channel: int
        :type amplitude: float
        """
        # Check channel
        channel = self.check_channel(channel=channel)
        # Get min and max
        min_amp = float(self.query("SOURCE{0}:AMPLITUDE? MIN".format(channel)))
        max_amp = float(self.query("SOURCE{0}:AMPLITUDE? MAX".format(channel)))
        # Check the amplitude and set
        if amplitude > max_amp:
            logger.warning("amplitude is greater than the max for the current "
                           "settings; setting to {0}".format(max_amp))
            self.write("SOURCE{0}:AMPLITUDE MAX".format(channel))
        elif amplitude < min_amp:
            logger.warning("amplitude is less than the min for the current "
                           "settings; setting to {0}".format(min_amp))
            self.write("SOURCE{0}:AMPLITUDE MIN".format(channel))
        else:
            command = "SOURCE{0}:AMPLITUDE {1}".format(channel, amplitude)
            self.write(command)

    def get_amplitude(self, channel):
        """ Query the channel's amplitude in units of Vpp

        :param channel: The chanel whose amplitude will be queried
        :type channel: int
        :return: The current amplitude in units of Vpp
        :rtype: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Query
        return float(self.query("SOURCE{0}:AMPLITUDE?".format(channel)))

    def set_dcoffset(self, channel, offset):
        """ Sets the channel's DC offset

        The min and max of the DC offset depends on the current amplitude
        (among other things).  This method will query the current max and min
        and warn the user if the specified value is out of range.  If the
        specified value is out of range, then the offset will be set to the
        min/max.

        :param channel: The channel whose offset will be set
        :param offset: The offset in Volts
        :type channel: int
        :type offset: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Get min and max
        min_off = float(self.query("SOURCE{0}:DCOFFSET? MIN".format(channel)))
        max_off = float(self.query("SOURCE{0}:DCOFFSET? MAX".format(channel)))
        # Check the offset and set
        if offset > max_off:
            logger.warning("offset is greater than the max for the current "
                           "settings; setting to {0}".format(max_off))
            self.write("SOURCE{0}:DCOFFSET MAX".format(channel))
        elif offset < min_off:
            logger.warning("offset is less than the min for the current "
                           "settings; setting to {0}".format(min_off))
            self.write("SOURCE{0}:DCOFFSET MIN".format(channel))
        else:
            command = "SOURCE{0}:DCOFFSET {1}".format(channel, offset)
            self.write(command)

    def get_dcoffset(self, channel):
        """ Queries the channel's current DC offset

        :param channel: The chanel whose offset will be queried
        :type channel: int
        :return: The current offset in units of Volts
        :rtype: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Query channel
        return float(self.query("SOURCE{0}:DCOFFSET?".format(channel)))

    def set_square_duty(self, channel, duty):
        """ Sets the duty cycle for the square waveform

        The duty cycle which the AFG 2225 can generate depends on the
        frequency of the square wave.  This method will query the max and min
        and warn the user if the specified duty is outside of that range.  It
        will also set the duty to the max or min in that situation.

        :param channel: The channel whose duty cycle will be set
        :param duty: Duty cycle in percent: 1-99
        :type channel: int
        :type duty: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Get min and max
        min_duty = float(self.query("SOURCE{0}:SQUARE:DCYCLE? MIN".format(channel)))
        max_duty = float(self.query("SOURCE{0}:SQUARE:DCYCLE? MAX".format(channel)))
        # Check the offset and set
        if duty > max_duty:
            logger.warning("duty is greater than the max for the current "
                           "settings; setting to {0}".format(max_duty))
            self.write("SOURCE{0}:SQUARE:DCYCLE MAX".format(channel))
        elif duty < min_duty:
            logger.warning("duty is less than the min for the current "
                           "settings; setting to {0}".format(min_duty))
            self.write("SOURCE{0}:SQUARE:DCYCLE MIN".format(channel))
        else:
            command = "SOURCE{0}:SQUARE:DCYCLE {1}".format(channel, duty)
            self.write(command)

    def get_square_duty(self, channel):
        """ Queries the current square wave duty cycle for the specified channel

        :param channel: The channel whose duty cycle will be queried
        :type channel: int
        :return: The current duty cycle
        :rtype: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Query
        return float(self.query("SOURCE{0}:SQUARE:DCYCLE?".format(channel)))

    def set_ramp_symmetry(self, channel, symmetry):
        """ Sets the symmetry parameter for the ramp waveform


        :param channel: The channel whose duty cycle will be set
        :param symmetry: Symmetry in percent: 0-100
        :type channel: int
        :type symmetry: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Get min and max
        min_sym = float(self.query("SOURCE{0}:RAMP:SYMMETRY? MIN".format(channel)))
        max_sym = float(self.query("SOURCE{0}:RAMP:SYMMETRY? MAX".format(channel)))
        # Check the offset and set
        if symmetry > max_sym:
            logger.warning("symmetry is greater than the max for the current "
                           "settings; setting to {0}".format(max_sym))
            self.write("SOURCE{0}:RAMP:SYMMETRY MAX".format(channel))
        elif symmetry < min_sym:
            logger.warning("symmetry is less than the min for the current "
                           "settings; setting to {0}".format(min_sym))
            self.write("SOURCE{0}:RAMP:SYMMETRY MIN".format(channel))
        else:
            command = "SOURCE{0}:RAMP:SYMMETRY {1}".format(channel, symmetry)
            self.write(command)

    def get_ramp_symmetry(self, channel):
        """ Queries the current ramp symmetry for the specified channel

        :param channel: The channel whose symmetry will be queried
        :type channel: int
        :return: The current symmetry setting
        :rtype: float
        """
        # Check channel
        channel = self.check_channel(channel)
        # Query
        return float(self.query("SOURCE{0}:RAMP:SYMMETRY?".format(channel)))

    ###########################################################################
    # Set/Get Interface Properties
    ###########################################################################
    def set_voltageunits(self, channel, unit='VPP'):
        """ Sets the current units used to specify the voltage

        :param channel: The channel whose units will be set
        :param unit: One of ['VPP', 'VRMS', 'DBM']
        :type channel: int
        :type unit: str
        """
        # Check channel
        channel = self.check_channel(channel)
        # Check unit
        unit = unit.upper()
        unit_list = ['VPP', 'VRMS', 'DBM']
        if unit not in unit_list:
            best_match = self.get_close_string(unit, unit_list)
            if best_match is None:
                raise ValueError("unit does not match any possible units")
            else:
                logger.warning("{0} does not match any function; using {1} "
                               "instead".format(unit, best_match))
            unit = best_match
        # Set unit
        command = "SOURCE{0}:VOLTAGE:UNIT {1}".format(channel, unit)
        self.write(command)

    def get_voltageunits(self, channel):
        """ Queries the channel's current voltage unit

        :param channel: The channel whose units will be queried
        :type channel: int
        :return: The current unit of the channel
        :rtype: str
        """
        # Check channel
        channel = self.check_channel(channel)
        # Query channel
        return self.query("SOURCE{0}:VOLTAGE:UNIT?".format(channel))







