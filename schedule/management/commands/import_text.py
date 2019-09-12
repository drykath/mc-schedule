from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import csv
import re
from datetime import datetime, time

from schedule.models import Panel, Room, Track
# TODO: Need to abstract this link still...
from convention.models import Convention

class Command(BaseCommand):
    help = 'Import schedule from a specially formatted text file'

    def add_arguments(self, parser):
        parser.add_argument('txt_path', type=str)

        parser.add_argument(
            '--clear',
            action='store_true',
            dest='clear',
            default=False,
            help='Removal all schedule items from the convention before import'
        )
        parser.add_argument(
            '--append',
            action='store_true',
            dest='append',
            default=False,
            help='Add all scheduled panels from the import file, even if the convention has panels already. Risks duplicates.'
        )

    def save_panel(self, panel, track, convention):
        item = Panel.objects.create(
            convention = convention,
            title = panel['title'],
            track = track,
            room = panel['room'],
            hosts = panel['hosts'],
            description = panel['description'],
        )

        item.schedule.create(
            day = panel['day'],
            start_time = panel['start_time'],
            end_time = panel['end_time'],
        )

    @transaction.atomic
    def handle(self, *args, **options):
        # XXX: The parser may need to be tuned depending on source data details

        convention = Convention.objects.current()

        existing = Panel.objects.filter(convention=convention)
        if len(existing) > 0:
            if options['clear']:
                existing.delete()
                for room in Room.objects.filter(convention=convention):
                    room.schedule.clear()
            else:
                if not options['append']:
                    raise CommandError('Convention already has panels, cannot import without --append or --clear')

        # Cache the Room and Track objects by name
        rooms = Room.objects.filter(convention=convention)
        room_cache = {room.name: room for room in rooms}
        # If the room is called a different thing, or has a specific purpose
        room_cache.update({room.alias: room for room in rooms if room.alias})

        tracks = Track.objects.filter(convention=convention)
        track_cache = {track.name: track for track in tracks}

        # Maps to correct shortcuts in the source data
        time_map = {
            'Always Open': ['Thursday 6:00 PM - 12:30 AM', 'Friday 09:00 AM - 2:00 AM', 'Saturday 09:00 AM - 2:00 AM', 'Sunday 09:00 AM - 2:00 AM'],
        }
        time_regex = re.compile('^(?P<day>\w+) (?P<shour>\d+):(?P<sminute>\d{2}) (?P<smeridian>\w{2}) - (?P<ehour>\d+):(?P<eminute>\d{2}) (?P<emeridian>\w{2})\s*$')
        time_days = {
            'Thursday': 3,
            'Friday': 4,
            'Saturday': 5,
            'Sunday': 6,
        }

        with open(options['txt_path'], 'r') as schedulefile:
            nextline = None
            track = None
            panel = None
            for line in schedulefile:
                line = line.rstrip('\n')

                if line == "":
                    # Save what we've gathered so far
                    if nextline and nextline != 'title':
                        self.save_panel(panel, track, convention)

                    # Reset state for the next item
                    panel = {
                        'title': None,
                        'room': None,
                        'day': None,
                        'start_time': None,
                        'end_time': None,
                        'hosts': None,
                        'description': None,
                    }
                    nextline = 'title'
                    continue

                if line in track_cache.keys():
                    track = track_cache[line]
                    continue

                if nextline == 'title':
                    panel['title'] = line
                    nextline = 'room_day_time'
                elif nextline == 'room_day_time':
                    room, times = line.split(' - ', 1)
                    panel['room'] = room_cache[room]

                    time_info = time_regex.search(times)
                    if not time_info:
                        raise Exception('Bad time information in line {}'.format(line))
                    time_info = time_info.groupdict()
                    panel['day'] = time_days[time_info['day']]
                    # Special case, make 24:00 into 0:00 midnight
                    if time_info['smeridian'] == 'PM' and time_info['shour'] != '12':
                        time_info['shour'] = int(time_info['shour']) + 12
                    if time_info['emeridian'] == 'PM' and time_info['ehour'] != '12':
                        time_info['ehour'] = int(time_info['ehour']) + 12
                    if int(time_info['shour']) == 24:
                        time_info['shour'] = 0
                    if int(time_info['ehour']) == 24:
                        time_info['ehour'] = 0
                    panel['start_time'] = time(int(time_info['shour']), int(time_info['sminute']))
                    panel['end_time'] = time(int(time_info['ehour']), int(time_info['eminute']))

                    nextline = 'hosts'
                elif nextline == 'hosts':
                    panel['hosts'] = line
                    nextline = 'description'
                elif nextline == 'description':
                    if panel['description']:
                        panel['description'] += '\n{}'.format(line)
                    else:
                        panel['description'] = line

            # Assuming there isn't a blank line at the end save the last
            self.save_panel(panel, track, convention)

