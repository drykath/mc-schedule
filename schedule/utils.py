from datetime import datetime, date, time, timedelta

from django.conf import settings

class contime(time):
    '''
    Modified time that for sorting and display purposes has a different
    day transition other than midnight. Only cares about hour and
    minute, seconds, microseconds, and tzinfo are ignored.

    Set SCHEDULE_DAY_TRANSITION_HOUR in settings, otherwise is 4 AM by
    default. (Nychthemeron seems to be the word. But nobody knows what
    that is.)
    '''

    def __new__(cls, hour=0, minute=0):
        '''
        Constructor, arguments exactly like the time class, except also
        can take a time object in the first parameter for casting,
        ignoring anything but the hour and minute.
        '''

        if isinstance(hour, time):
            self = time.__new__(cls, hour=hour.hour, minute=hour.minute)
        elif isinstance(hour, bytes) and len(hour) == 6 and hour[0]&0x7F < 24:
            # Pickle support
            self = time.__new__(cls, hour)
        else:
            self = time.__new__(cls, hour, minute)
        self._horizon = self.day_transition_hour()

        return self

    @staticmethod
    def day_transition_hour():
        return getattr(settings, 'SCHEDULE_DAY_TRANSITION_HOUR', 4)

    # Comparisons

    # eq is good, even support equating to the base time type if needed

    def __le__(self, other):
        if type(other) == contime:
            return self._cmp(other) <= 0
        else:
            self._cmperror(other)

    def __lt__(self, other):
        if type(other) == contime:
            return self._cmp(other) < 0
        else:
            self._cmperror(other)

    def __ge__(self, other):
        if type(other) == contime:
            return self._cmp(other) >= 0
        else:
            self._cmperror(other)

    def __gt__(self, other):
        if type(other) == contime:
            return self._cmp(other) > 0
        else:
            self._cmperror(other)

    def _cmp(self, other, allow_mixed=False):
        assert isinstance(other, time)
        # Anything 'before' the hour horizon is actually late in the day
        x = (self.hour + 24 if self.hour < self._horizon else self.hour, self.minute)
        y = (other.hour + 24 if other.hour < self._horizon else other.hour, other.minute)
        return 0 if x == y else 1 if x > y else -1

    def _cmperror(self, other):
        raise TypeError("can't compare '%s' to '%s'" % (
            type(self).__name__, type(other).__name__))

    # Methods

    # Support timedelta, or what we care about it
    def __add__(self, other):
        "Add a contime and a timedelta's hours and minutes"
        if not isinstance(other, timedelta):
            return NotImplemented

        hours, rem = divmod(other.seconds, 3600)
        minutes, seconds = divmod(rem, 60)

        if other.days or other.microseconds or seconds:
            raise ValueError('Can combine timedeltas with hours and minutes only')

        new_hour = self.hour + hours
        new_minute = self.minute + minutes

        if new_minute >= 60:
            new_hour += 1
            new_minute -= 60
        if new_hour >= 24:
            new_hour -= 24

        return contime(new_hour, new_minute)


def time_range(start, end, minutes=30):
    '''
    Generates a series of contime's between start and end at (minutes)
    intervals.
    '''

    delta = timedelta(minutes=minutes)

    while start < end:
        yield start
        start += delta

def time_round(tm, minutes=30):
    '''
    Accepts a datetime.time or contime object, and rounds to the nearest
    (minutes) interval. Used for ensuring alignment to calendar view.
    '''

    delta = timedelta(minutes=minutes)
    if type(tm) == time:
        new_dt = datetime.combine(date.min, tm) + (delta/2)
        new_minute = (new_dt.minute//minutes) * minutes
        return new_dt.time().replace(minute=new_minute, second=0, microsecond=0)
    elif type(tm) == contime:
        new_time = tm + (delta/2)
        new_minute = (new_time.minute//minutes) * minutes
        return contime(new_time.hour, new_minute)
    else:
        raise ValueError("Can't round '%s' as a time value" % (
            type(tm).__name__))
