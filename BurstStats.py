from saleae.range_measurements import DigitalMeasurer
from math import sqrt

class RunningSD:
    def __init__(self):
        self.n = 0
        self.oldMean = 0
        self.oldSum = 0

    def add(self, value):
        self.n += 1

        if self.n < 2:
            self.oldMean = value
            self.newMean = value
            self.oldSum = 0.0
            return

        self.newMean = self.oldMean + (value - self.oldMean) / float(self.n)
        self.newSum = self.oldSum + (value - self.oldMean) * (value - self.newMean)
        self.oldMean = self.newMean
        self.oldSum = self.newSum

    def StdDev(self):
        if self.n > 1:
            return sqrt(self.newSum / float(self.n - 1))

        return 0.0

class BurstStatsMeasurer(DigitalMeasurer):
    supported_measurements = ['pPMin', 'pPMax', 'pPSDev', 'pCount']

    '''
    Initialize BurstStatsMeasurer object instance. An instance is created for
    each measurement session so this code is called once at the start of each
    measurement.

    process_data(...) is then called multiple times to process data in time
    order.

    After all data has been processed measure(...) is called to complete
    analysis and return a dictionary of results.
    '''
    def __init__(self, requested_measurements):
        super().__init__(requested_measurements)
        self.pPMin = None
        self.pPMean = 0.0
        self.pPMax = None
        self.lastState = None
        self.burstStart = None
        self.lastEdge = None
        self.PSDev = RunningSD()
        self.LSDev = RunningSD()
        self.periods = 0

        # 'User' parameters
        self.kMinPeriod = 4e-6    # minimum time with no edges between bursts

        # Set wantedState True (rising edge), False (falling edge) or None
        self.wantedState = False

    '''
    process_data() will be called one or more times per measurement with batches
    of data.

    data has the following interface:

      * Iterate over data to get transitions in the form of pairs of
        `Time`, Bitstate (`True` for high, `False` for low)

      * The first datum is at the first transition

    `Time` currently only allows taking a difference with another `Time`, to
    produce a `float` number of seconds
    '''
    def process_data(self, data):

        for t, bitstate in data:
            if not self.wantedState is None and bitstate != self.wantedState:
                # Wrong edge type. Skip
                continue

            if self.lastState is None:
                self.lastState = bitstate
                self.lastEdge = t
                self.burstStart = t
                self.periods = 0

                # Can't generate stats for the first Burst
                continue

            timeDelta = float(t - self.lastEdge)
            self.lastEdge = t

            if timeDelta < self.kMinPeriod:
                # We need the time from the last Burst to be at least
                # self.kMinPeriod to accept this Burst as the start of a new
                # burst
                continue

            # high going Edge. End/Start of a burst
            timeDelta = float(t - self.burstStart)
            self.burstStart = t

            self.pPMean += timeDelta
            self.PSDev.add(timeDelta)
            self.periods += 1

            if self.pPMin == None or timeDelta < self.pPMin:
                self.pPMin = timeDelta

            if self.pPMax == None or timeDelta > self.pPMax:
                self.pPMax = timeDelta

    '''
    measure(...) is called after all the relevant data has been processed by
    process_data(...). It returns a dictionary of measurement results.
    '''
    def measure(self):
        values = {}

        if self.periods:
            values['pPMin'] = self.pPMin
            values['pPMean'] = self.pPMean / self.periods
            values['pPMax'] = self.pPMax
            values['pPSDev'] = self.PSDev.StdDev()
            values['pBursts'] = self.periods + 1
        else:
            values['pPMin'] = 0
            values['pPMean'] = 0
            values['pPMax'] = 0
            values['pPSDev'] = 0
            values['pBursts'] = 0

        return values
