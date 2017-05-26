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

logger = logging.getLogger()


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
    # Direct Set Methods
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




