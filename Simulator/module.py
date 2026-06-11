# The Basic class for the modules. Provides all the very lowest level services such as responding to the clock tick.
#
#
#


class Module:
    def __init__(self, name: str):
        self.name = name
        pass

    def getName(self) -> str:
        return self.name

    def clock_pulse(self) -> None:
        """
        Respond to a tick of the clock. Should only be called by the Singleton clock object.
        """

        pass

    def clock_inv_pulse(self) -> None:
        """
        Respond to an inverse tick of the clock. Should only be called by the Singleton clock object.
        """
        pass
