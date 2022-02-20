from datetime import datetime, timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone

from django.contrib.auth import get_user_model
from convention import get_convention_model

from .utils import contime, time_range

Convention = get_convention_model()


class Panel(models.Model):
    convention = models.ForeignKey(Convention, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    track = models.ForeignKey('Track', on_delete=models.PROTECT)
    room = models.ForeignKey('Room', on_delete=models.PROTECT)
    hosts = models.TextField(max_length=255)
    hidden = models.BooleanField(default=False)
    description = models.TextField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    attendees = models.ManyToManyField(get_user_model(), through='Attendee')
    map_image = models.FileField(
        upload_to=getattr(settings, 'SCHEDULE_MEDIA_UPLOAD_TO', 'schedule/'),
        null=True, blank=True)

    def __str__(self):
        return self.title


class Room(models.Model):
    convention = models.ForeignKey(Convention, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    alias = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(
        'description on schedule',
        null=True, blank=True,
        help_text='Only needed if this room has open/close times')
    sort_order = models.IntegerField(null=True, blank=True)
    track = models.ForeignKey(
        'Track', on_delete=models.PROTECT,
        null=True, blank=True,
        help_text='Only needed if this room has open/close times')
    location_hint = models.CharField(max_length=255, null=True, blank=True)
    always_open = models.BooleanField(default=False)
    map_image = models.FileField(
        upload_to=getattr(settings, 'SCHEDULE_MEDIA_UPLOAD_TO', 'schedule/'),
        null=True, blank=True)

    class Meta:
        ordering = ['convention', 'sort_order']
        unique_together = (
            ('convention', 'name'),
        )

    def __str__(self):
        return self.name


class ItemSchedule(models.Model):
    # Based on datetime.weekday()
    # Also herein is an assumption that the convention ends on Sunday.
    WEEKDAYS = (
        (3, 'Thursday'),
        (4, 'Friday'),
        (5, 'Saturday'),
        (6, 'Sunday'),
        # Please tell me we will never need these
        (0, 'Monday'),
        (1, 'Tuesday'),
        (2, 'Wednesday'),
    )
    day = models.IntegerField(choices=WEEKDAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()

    class Meta:
        abstract = True

    @property
    def start_contime(self):
        'Returns the start time cast as a contime object'
        return contime(self.start_time)

    @property
    def end_contime(self):
        'Returns the end time cast as a contime object'
        return contime(self.end_time)

    @property
    def start_timestamp(self):
        "Try to compute this panel's real start time and date"
        if hasattr(self, 'panel'):
            parent = self.panel
        else:
            parent = self.room
        con_start = parent.convention.start_date
        con_start_normalized = con_start - timedelta(days=con_start.weekday())

        panel_day = con_start_normalized + timedelta(days=self.day)
        panel_dt = datetime.combine(panel_day, self.start_time).replace(
            tzinfo=timezone.get_current_timezone())

        # Correct the timestamp if we've transitioned into the next day
        if panel_dt.hour < contime.day_transition_hour():
            panel_dt += timedelta(days=1)

        return panel_dt

    @property
    def end_timestamp(self):
        "Try to compute this panel's real start time and date"
        if hasattr(self, 'panel'):
            parent = self.panel
        else:
            parent = self.room
        con_start = parent.convention.start_date
        con_start_normalized = con_start - timedelta(days=con_start.weekday())

        panel_day = con_start_normalized + timedelta(days=self.day)
        panel_dt = datetime.combine(panel_day, self.end_time).replace(
            tzinfo=timezone.get_current_timezone())

        # Correct the timestamp if we've transitioned into the next day
        if panel_dt.hour < contime.day_transition_hour():
            panel_dt += timedelta(days=1)

        return panel_dt

    @property
    def past(self):
        '''Try to determine if this panel is over'''
        if self.end_timestamp < timezone.now().replace(tzinfo=timezone.get_current_timezone()):
            return True
        return False

    def adjust_render_start(self, tm):
        self._render_start = tm

    def grid_draw_height(self):
        '''Returns the number of half-hour blocks for this panel.'''

        if hasattr(self, '_render_start'):
            start = self._render_start
        else:
            start = self.start_contime
        return len(list(time_range(start, self.end_contime)))


class PanelSchedule(ItemSchedule):
    panel = models.ForeignKey(Panel, on_delete=models.CASCADE,
                              related_name='schedule')


class RoomSchedule(ItemSchedule):
    room = models.ForeignKey(Room, on_delete=models.CASCADE,
                             related_name='schedule')


class Track(models.Model):
    convention = models.ForeignKey(Convention, on_delete=models.CASCADE)
    name = models.CharField(max_length=100)
    class_name = models.CharField(max_length=25)
    color = models.CharField(max_length=10) # TODO: css_color

    class Meta:
        ordering = ['convention', 'name']
        unique_together = (
            ('convention', 'name'),
            ('convention', 'class_name'),
        )

    def __str__(self):
        return self.name


class Attendee(models.Model):
    user = models.ForeignKey(get_user_model(), on_delete=models.PROTECT)
    panel = models.ForeignKey(Panel, on_delete=models.PROTECT)
    starred = models.BooleanField(default=False)
    hide_from_user = models.BooleanField(default=False)
    attended = models.BooleanField(null=True)
    feedback = models.TextField(null=True, blank=True)

    class Meta:
        unique_together = (
            ('user', 'panel'),
        )
