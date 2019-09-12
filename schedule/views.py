from collections import OrderedDict

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch
from django.http import Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.cache import cache_control
from django.views.generic import View
from icalendar import Calendar, Event, vText
from json import dumps as json_dumps

from convention import get_convention_model

from .crypto import create_token, parse_token
from .models import Attendee, Panel, PanelSchedule, RoomSchedule, Track
from .utils import contime, time_range, time_round

current_convention = get_convention_model().objects.current()


class Schedule(View):
    '''
    Base class of a view that reads in all the relevant data for a given
    convention's panel and room schedules, to prepare for generating the
    page for the end user.

    Subclasses should define a template_name, and a pack_struct() method
    that prepares a structure for the given template, whatever that
    structure needs to look like, and returns a dict that's included in
    the template's context.
    '''
    template_name = None
    preload_panels_rooms = False
    convention = None
    user = None

    def dispatch(self, request, addl_filter='', convention=None, **kwargs):
        # Load in convention and user instance variables
        self.convention = convention
        if not convention:
            self.convention = current_convention
        if not self.user and request.user.is_authenticated:
            self.user = request.user

        if not getattr(settings, 'SCHEDULE_IS_PUBLIC', True):
            if not request.user.is_authenticated or \
                    not request.user.is_staff:
                raise Http404()

        # Do some request sanity checking
        if addl_filter not in ['', 'custom', 'all']:
            raise Http404()
        if addl_filter == 'custom' and not self.user:
            # Redirect users not logged in requesting a custom schedule
            response = redirect('login')
            response['Location'] += '?next={}'.format(request.path)
            return response
        self.addl_filter = addl_filter

        return super().dispatch(request, addl_filter=addl_filter, convention=convention, **kwargs)

    def get(self, request, addl_filter='', convention=None):
        if self.preload_panels_rooms:
            self.load_panels_rooms()
        structure = self.pack_struct()

        context = {
            'addl_filter': addl_filter,
            'track_filter': request.GET['track'] if 'track' in request.GET.keys() else None,
            'convention': self.convention,
            'request_user': request.user,
            'today': None,  # TODO: Today detection for tab auto-selection
            'auth_token': create_token(request.user),
            'tracks': Track.objects.filter(convention=self.convention),
        }
        context.update(structure)

        return render(request, self.template_name, context)

    def pack_struct(self):
        raise NotImplementedError

    def load_panels_rooms(self):
        '''
        Load in the panels and rooms lists based on the logged in user,
        the requested preset filter, and time for a given convention.
        '''
        self.panelschedules = PanelSchedule.objects.select_related(
            'panel', 'panel__convention', 'panel__room', 'panel__track'
        ).filter(
            panel__convention=self.convention, panel__hidden=False
        ).order_by('day')
        self.roomschedules = RoomSchedule.objects.select_related(
            'room', 'room__convention', 'room__track'
        ).filter(
            room__convention=self.convention
        ).order_by('day')

        if self.addl_filter != 'all':
            # Filter our not-all views by date, and later time, if the convention has started
            if self.convention == current_convention \
                and self.convention.start_date < timezone.now().date():
                self.panelschedules = self.panelschedules.exclude(
                    day__lt=self.convention.start_date.weekday())
                # Room schedules can't be commented on or excluded, but still do time exclusions
                self.roomschedules = self.roomschedules.exclude(
                    day__lt=self.convention.start_date.weekday())

            # Apply additional filtering if the user has logged in
            if self.user:
                if self.addl_filter == '':
                    self.panelschedules = self.panelschedules.exclude(
                        panel__attendee__in=Attendee.objects.filter(
                            user=self.user, hide_from_user=True))
                if self.addl_filter == 'custom':
                    self.panelschedules = self.panelschedules.filter(
                        panel__attendee__user=self.user, panel__attendee__starred=True)
                    self.roomschedules = RoomSchedule.objects.none()

        if 'track' in self.request.GET.keys():
            track = get_object_or_404(Track, name=self.request.GET['track'], convention=current_convention)
            self.panelschedules = self.panelschedules.filter(panel__track=track)
            self.roomschedules = self.roomschedules.filter(room__track=track)

        if self.user:
            # Pre-fetch any preference records for this attendee
            self.panelschedules = self.panelschedules.prefetch_related(
                Prefetch('panel__attendee_set',
                         queryset=Attendee.objects.filter(user=self.user),
                         to_attr='attendee_info'))
        return (self.panelschedules, self.roomschedules)

    def create_base_days_structure(self):
        '''
        Utility function, creates an OrderedDict of day to sub-dict with
        keys we'll expect to use, currently:
        - range: a 2-list with lower bound, upper bound contimes per day
        - panelschedules: PanelSchedules that apply to this day
        - roomschedules: RoomSchedules that apply to this day
        '''
        days = {}
        shortened_day = None
        now = timezone.now().replace(tzinfo=timezone.get_current_timezone())

        for panelschedule in self.panelschedules:
            # Skip any panel that's ended
            if self.addl_filter != 'all' and panelschedule.end_timestamp < now:
                # If we catch a panel excluded by time, assume we're rendering today
                shortened_day = panelschedule.day
                continue
            # Scan the existing schedules to build the daily time ranges and list of rooms
            panel_day = panelschedule.get_day_display()
            if panel_day not in days:
                days[panel_day] = {
                    'panelschedules': [panelschedule],
                    'range': [time_round(panelschedule.start_contime),
                              time_round(panelschedule.end_contime)],
                    'roomschedules': [],
                }
            else:
                days[panel_day]['panelschedules'].append(panelschedule)
                # Check panel against our existin range, expand if needed
                if days[panel_day]['range'][0] > time_round(panelschedule.start_contime):
                    days[panel_day]['range'][0] = time_round(panelschedule.start_contime)
                if days[panel_day]['range'][1] < time_round(panelschedule.end_contime):
                    days[panel_day]['range'][1] = time_round(panelschedule.end_contime)

        for roomschedule in self.roomschedules:
            # Skip any room that's closed
            if self.addl_filter != 'all' and roomschedule.end_timestamp < now:
                continue
            # Same thing, see if we need to adjust the day's render range
            room_day = roomschedule.get_day_display()
            if room_day not in days:
                days[room_day] = {
                    'panelschedules': [],
                    'range': [time_round(roomschedule.start_contime),
                              time_round(roomschedule.end_contime)],
                    'roomschedules': [roomschedule],
                }
            else:
                days[room_day]['roomschedules'].append(roomschedule)
                # If we've started hiding panels, move room starts down
                if roomschedule.day != shortened_day:
                    if days[room_day]['range'][0] > time_round(roomschedule.start_contime):
                        days[room_day]['range'][0] = time_round(roomschedule.start_contime)
                if days[room_day]['range'][1] < time_round(roomschedule.end_contime):
                    days[room_day]['range'][1] = time_round(roomschedule.end_contime)

        # Put days in order
        ordered_days = OrderedDict()
        for day_number, day_display in PanelSchedule.WEEKDAYS:
            if day_display in days:
                ordered_days[day_display] = days[day_display]

        return ordered_days


class ScheduleList(Schedule):
    template_name = 'schedule/list.html'
    preload_panels_rooms = True

    def pack_struct(self):
        days = self.create_base_days_structure()

        # Fill in the structure we want to render
        for day, day_struct in days.items():
            # Our list schedule is a dict of time slots...
            day_struct['schedule'] = OrderedDict()
            for tm in time_range(day_struct['range'][0], day_struct['range'][1]):
                # ... That point to a list of schedule items
                day_struct['schedule'][tm] = []

            # Then assign the panels into those lists
            for panelschedule in day_struct['panelschedules']:
                day_struct['schedule'][time_round(panelschedule.start_contime)].append(panelschedule)
            for roomschedule in day_struct['roomschedules']:
                # If we've started cutting off, move the displayed room opening to start where we start drawing
                if time_round(roomschedule.start_contime) < day_struct['range'][0]:
                    day_struct['schedule'][day_struct['range'][0]].append(roomschedule)
                else:
                    day_struct['schedule'][time_round(roomschedule.start_contime)].append(roomschedule)

            # We no longer need the lists by day, save some cache space
            del day_struct['panelschedules']
            del day_struct['roomschedules']

        return {'days': days}


class ScheduleGrid(Schedule):
    template_name = 'schedule/grid.html'
    preload_panels_rooms = True
    # Cell templates
    template_no_panel = 'schedule/grid_cell_no_panel.html'
    template_start_panel = 'schedule/grid_cell_start_panel.html'
    template_running_panel = 'schedule/grid_cell_running_panel.html'
    template_open_room = 'schedule/grid_cell_open_room.html'
    template_close_room = 'schedule/grid_cell_close_room.html'

    def pack_struct(self):
        days = self.create_base_days_structure()

        # Fill in the structure we want to render
        for day, day_struct in days.items():
            # Figure out which rooms are used this day
            day_struct['rooms'] = list(set(
                [roomschedule.room for roomschedule in day_struct['roomschedules']] +
                [panelschedule.panel.room for panelschedule in day_struct['panelschedules']]
            ))
            # Display the rooms in requested order
            day_struct['rooms'].sort(key=lambda room: room.sort_order if room.sort_order else 99)

            # Our list schedule is a dict of time slots...
            day_struct['schedule'] = OrderedDict()
            for tm in time_range(day_struct['range'][0], day_struct['range'][1]):
                # ... That point to an OrderedDict of rooms to cell contents
                day_struct['schedule'][tm] = OrderedDict()
                for room in day_struct['rooms']:
                    day_struct['schedule'][tm][room] = {
                        'panelschedule': None,
                        'roomschedule': None,
                        'cell_template': self.template_no_panel,
                    }

            # Then assign the rooms into those structures
            for roomschedule in day_struct['roomschedules']:
                for tm in time_range(time_round(roomschedule.start_contime),
                                     time_round(roomschedule.end_contime)):
                    if tm < day_struct['range'][0]:
                        continue
                    day_struct['schedule'][tm][roomschedule.room]['roomschedule'] = roomschedule
                    last_time_slot = tm
                # Then override the templates for the start and end cells
                # If we've started cutting off, move the displayed room opening
                if time_round(roomschedule.start_contime) < day_struct['range'][0]:
                    day_struct['schedule'][day_struct['range'][0]][roomschedule.room]['cell_template'] = self.template_open_room
                else:
                    day_struct['schedule'][time_round(roomschedule.start_contime)][roomschedule.room]['cell_template'] = self.template_open_room
                day_struct['schedule'][last_time_slot][roomschedule.room]['cell_template'] = self.template_close_room
            # And then the same for panels, which overrides any room template decision
            for panelschedule in day_struct['panelschedules']:
                for tm in time_range(time_round(panelschedule.start_contime), time_round(panelschedule.end_contime)):
                    day_struct['schedule'][tm][panelschedule.panel.room]['panelschedule'] = panelschedule
                    # Default to the running_panel template
                    day_struct['schedule'][tm][panelschedule.panel.room]['cell_template'] = self.template_running_panel
                # But replace the first cell with the starting panel template
                day_struct['schedule'][time_round(panelschedule.start_contime)][panelschedule.panel.room]['cell_template'] = self.template_start_panel

            # We no longer need the lists by day, save some cache space
            del day_struct['panelschedules']
            del day_struct['roomschedules']

        return {'days': days}


class SerializedSchedule(Schedule):
    """Abstract subclass that packs the schedule into some other format"""

    def dispatch(self, request, auth_token=None, **kwargs):
        # If we've been given an auth token, try to parse into user
        if auth_token:
            user = parse_token(auth_token)
            if user:
                # Don't need to do a proper logon, just stash the user
                # object for the subsequent queries.
                self.user = user
        # Superclass's dispatch should load in user if we didn't here
        return super().dispatch(request, auth_token=auth_token, **kwargs)


class ScheduleICS(SerializedSchedule):
    """Makes an ICS file rather than HTML"""

    def get(self, request, addl_filter='', **kwargs):
        panelschedules, roomschedules = self.load_panels_rooms()

        cal = Calendar()
        cal.add('prodid', '-//Motor City Furry Con//mcfc_schedule//EN')
        cal.add('version', '2.0')

        # Pack events into calendar
        for panelschedule in panelschedules:
            event = Event()
            event.add('dtstamp', timezone.now())
            event.add('dtstart', panelschedule.start_timestamp)
            event.add('dtend', panelschedule.end_timestamp)
            event.add('summary', vText(panelschedule.panel.title))
            event.add('description', vText('{description}\nHosts: {hosts}'.format(
                description=panelschedule.panel.description,
                hosts=panelschedule.panel.hosts)))
            event.add('contact', vText(panelschedule.panel.hosts))
            event.add('location', vText(panelschedule.panel.room.name))
            event.add('categories', vText(panelschedule.panel.track.name))
            event.add('uid', 'p{id}@{domain}'.format(
                id=panelschedule.id,
                domain=self.convention.site.domain))
            cal.add_component(event)

        for roomschedule in roomschedules:
            event = Event()
            event.add('dtstamp', timezone.now())
            event.add('dtstart', roomschedule.start_timestamp)
            event.add('dtend', roomschedule.end_timestamp)
            event.add('summary', vText(roomschedule.room.name + ' Open'))
            event.add('description', vText('{description}'.format(
                description=roomschedule.room.description)))
            event.add('location', vText(roomschedule.room.name))
            event.add('categories', vText(roomschedule.room.track.name))
            event.add('uid', 'r{id}@{domain}'.format(
                id=roomschedule.id,
                domain=self.convention.site.domain))
            cal.add_component(event)

        response = HttpResponse(cal.to_ical(), content_type='text/calendar')
        response['Content-Disposition'] = 'attachment; filename="{con}{filter}.ics"'.format(
            con=self.convention.name,
            filter=' ' + addl_filter if addl_filter else '',
        )
        return response


class ScheduleJSON(SerializedSchedule):
    """Makes JSON output rather than HTML, for future PWA use or such."""

    def get(self, request, addl_filter='', **kwargs):
        panelschedules, roomschedules = self.load_panels_rooms()

        panel_list = [{
            'title': panelschedule.panel.title,
            'description': panelschedule.panel.description,
            'hosts': panelschedule.panel.hosts,
            'start': str(panelschedule.start_timestamp),
            'end': str(panelschedule.end_timestamp),
            'room': panelschedule.panel.room.name,
            'track': panelschedule.panel.track.name,
            'type': 'panel'
        } for panelschedule in panelschedules]

        room_list = [{
            'title': roomschedule.room.name + ' Open',
            'description': roomschedule.room.description,
            'start': str(roomschedule.start_timestamp),
            'end': str(roomschedule.end_timestamp),
            'track': roomschedule.room.track.name,
            'type': 'room'
        } for roomschedule in roomschedules]

        event_struct = {
            'convention': current_convention.name,
            'events': panel_list + room_list,
        }

        response = HttpResponse(json_dumps(event_struct), content_type='text/json')
        return response


def panel_detail(request, panelschedule_id, **kwargs):
    '''
    Show detail info for a PanelSchedule item. May get a slug field in
    kwargs, but we don't really care about it; just for better links.
    '''
    try:
        panelobjects = PanelSchedule.objects
        if request.user.is_authenticated:
            panelobjects = panelobjects.prefetch_related(
                Prefetch('panel__attendee_set',
                         queryset=Attendee.objects.filter(user=request.user),
                         to_attr='attendee_info')
            )
        panelschedule = panelobjects.get(id=panelschedule_id)
    except PanelSchedule.DoesNotExist:
        raise Http404("No panel found with that ID.")

    other_times = panelschedule.panel.schedule.exclude(id=panelschedule.id)

    # Try to detect if we've come from the grid or list view
    # TODO: Might even be able to inspect urlpatterns. But for now...
    referer = None
    if 'HTTP_REFERER' in request.META:
        if 'grid' in request.META['HTTP_REFERER']:
            referer = 'schedule_grid'
        if 'list' in request.META['HTTP_REFERER']:
            referer = 'schedule_list'

    return render(request,
                  'schedule/panel_detail.html',
                  {
                    'panelschedule': panelschedule,
                    'other_times': other_times,
                    'referer': referer,
                    'request_user': request.user,
                  })

@cache_control(max_age=60*60*24)
def generate_css(request, convention=None):
    '''Gather track list for this convention and build CSS'''

    if not convention:
        convention = current_convention

    tracks = Track.objects.filter(convention=convention)

    return render(request,
                  'schedule/schedule.css',
                  {'tracks': tracks}, content_type='text/css')

@login_required
def set_preference(request, panel_id, pref=None):
    '''Adjust the settings object for a user on a given panel'''

    if not request.is_ajax() and pref is None:
        raise Http404()
    panel = get_object_or_404(Panel, id=panel_id)

    defaults = {}
    # TODO: Maybe worth doing a proper form here
    if 'attended' in request.POST.keys() and 'feedback' in request.POST.keys():
        defaults = {
            'attended': request.POST['attended'],
            'feedback': request.POST['feedback'],
        }

    # Set additional data based on URL
    if pref == 'star':
        defaults['starred'] = True
        defaults['hide_from_user'] = False
    if pref == 'unstar':
        defaults['starred'] = False
    if pref == 'hide':
        defaults['hide_from_user'] = True
        defaults['starred'] = False
    if pref == 'unhide':
        defaults['hide_from_user'] = False

    obj, created = Attendee.objects.update_or_create(
        user=request.user, panel=panel,
        defaults=defaults,
    )

    if request.is_ajax():
        return HttpResponse(status=204)
    return redirect('schedule_default')
