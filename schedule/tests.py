from django.test import TestCase

from datetime import datetime, time, timedelta

from convention.models import Convention
from convention.tests import create_test_convention

from .models import Panel, Room, Track
from .utils import contime, time_range, time_round

# Test Helpers

def create_test_panel(**kwargs):
        # Default values for a panel
        defaults = dict(
            title='Test Panel',
            hosts='Drykath',
        )
        # Override with those provided
        defaults.update(kwargs)

        if 'convention' not in defaults:
            defaults['convention'] = create_test_convention()
        if 'track' not in defaults:
            defaults['track'] = create_test_track(convention=defaults['convention'])
        if 'room' not in defaults:
            defaults['room'] = create_test_room(convention=defaults['convention'])

        return Panel.objects.create(
            **defaults
        )

def create_test_room(**kwargs):
        # Default values for a panel
        defaults = dict(
            name='Test Room',
        )
        # Override with those provided
        defaults.update(kwargs)

        if 'convention' not in defaults:
            defaults['convention'] = create_test_convention()

        return Room.objects.create(
            **defaults
        )

def create_test_track(**kwargs):
        # Default values for a panel
        defaults = dict(
            name='Test Track',
            class_name='test',
            color='gray',
        )
        # Override with those provided
        defaults.update(kwargs)

        if 'convention' not in defaults:
            defaults['convention'] = create_test_convention()

        return Track.objects.create(
            **defaults
        )

# Model tests
class PanelModelTestCase(TestCase):
    def test_model_name(self):
        panel = create_test_panel(title='Test')
        self.assertEqual(panel.title, str(panel))


class PanelScheduleModelTestCase(TestCase):
    def test_date_conversion(self):
        panel = create_test_panel(title='Test')
        panel.convention.start_date = datetime.today().date()
        panel.convention.save()

        panelschedule = panel.schedule.create(day=6,
            start_time=time(23, 0), end_time=time(1, 0))

        self.assertEqual(panelschedule.end_contime, panelschedule.end_time)
        # With the naive time, the end looks like it's before the start
        self.assertLess(panelschedule.end_time, panelschedule.start_time)
        # But end really should appear after the start time
        self.assertGreater(panelschedule.end_contime, panelschedule.start_contime)
        # Though if we cast to timestamp the days should be different
        self.assertNotEqual(panelschedule.start_timestamp.date(), panelschedule.end_timestamp.date())


class RoomModelTestCase(TestCase):
    def test_model_name(self):
        room = create_test_room(name='Test')
        self.assertEqual(room.name, str(room))


class TrackModelTestCase(TestCase):
    def test_model_name(self):
        track = create_test_track(name='Test')
        self.assertEqual(track.name, str(track))


# View tests

# Utility function tests
class ConTimeTypeTestCase(TestCase):
    def test_contime_type(self):
        # We should be able to define a time
        t = time(12, 0)
        # And then cast into contime
        ct = contime(t)
        self.assertEqual(t, ct)
        self.assertEqual(type(ct), contime)

        ct = contime(12, 0)
        self.assertEqual(t, ct)

    def test_contime_pickle(self):
        import pickle
        ct = contime(14, 45)
        # Support both pickle and unpickle to get the same value
        self.assertEqual(pickle.loads(pickle.dumps(ct)), ct)

    def test_contime_comparisons(self):
        # Using the default horizon of 4 AM
        pm11 = contime(23, 0)
        midnight = contime(0, 0)
        halfpast = contime(0, 30)
        am4 = contime(4, 0)

        self.assertGreater(midnight, pm11)
        self.assertGreaterEqual(halfpast, midnight)
        self.assertLess(am4, midnight)

    def test_contime_addition(self):
        am2 = contime(2, 0)
        delta = timedelta(hours=1)
        self.assertEqual(am2 + delta, contime(3, 0))
        self.assertLess(am2, am2 + delta)
        self.assertLessEqual(am2, am2)
        # Pushes us over the horizon
        self.assertGreater(am2, am2 + delta + delta)

    def test_contime_exceptions(self):
        ct = contime(12, 0)
        # Can't do comparisons on anything but other contime objects
        with self.assertRaises(TypeError):
            ct > 1
        with self.assertRaises(TypeError):
            ct >= 'a'
        with self.assertRaises(TypeError):
            ct < []
        # Even time objects
        with self.assertRaises(TypeError):
            ct <= time(12, 0)


class TimeRangeTestCase(TestCase):
    def test_time_range_random_time(self):
        # Test by assuming the run time is essentially a random value
        start = contime(4, 0)
        end = contime(16, 0)

        # Enumerate the generator into a list we can measure
        res = list(time_range(start, end, minutes=30))

        self.assertEqual(len(res), 24)


class TimeRoundTestCase(TestCase):
    def test_time_round_random_time(self):
        # Test by assuming the run time is essentially a random value
        now = datetime.now().time()
        rounded = time_round(now)

        self.assertIn(rounded.minute, [0, 30])
        self.assertEqual(rounded.second, 0)
        self.assertEqual(rounded.microsecond, 0)

    def test_time_round_random_contime(self):
        # Test by assuming the run time is essentially a random value
        now = contime(datetime.now().time())
        rounded = time_round(now)

        self.assertIn(rounded.minute, [0, 30])
        self.assertEqual(rounded.second, 0)
        self.assertEqual(rounded.microsecond, 0)
