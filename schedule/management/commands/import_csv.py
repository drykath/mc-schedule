from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

import csv
import re
from datetime import datetime, time

from schedule.models import Panel, Room, Track
# TODO: Need to abstract this link still...
from convention.models import Convention

class Command(BaseCommand):
    help = 'Import schedule from a specially formatted CSV file'

    def add_arguments(self, parser):
        parser.add_argument('csv_path', type=str)

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

    @transaction.atomic
    def handle(self, *args, **options):
        # XXX: The CSV parser may need to be tuned depending on source data details

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
            'Always Open': ['THU: 1800-0030', 'FRI: 0900-0200', 'SAT: 0900-0200', 'SUN: 0900-0200'],
        }
        time_regex = re.compile('^(?P<day>\w{3}): (?P<shour>\d{2})(?P<sminute>\d{2})-(?P<ehour>\d{2})(?P<eminute>\d{2})\s*$')
        time_days = {
            'THU': 3,
            'FRI': 4,
            'SAT': 5,
            'SUN': 6,
        }

        with open(options['csv_path'], 'r') as schedulefile:
            for row in csv.DictReader(schedulefile):
                # Ignore items not really on the schedule
                if row['Room / Time'] == 'Unscheduled' or row['Room / Time'].startswith('CANCELLED'):
                    continue
                if 'Exclude' in row and row['Exclude'] == 'Yes':
                    continue

                # Map rooms and times
                room_label = row['Room / Time'].split('\n')[-1]

                if row['Panel Name'] in room_cache.keys():
                    item = room_cache[row['Panel Name']]
                else:
                    item = Panel.objects.create(
                        convention = convention,
                        title = row['Panel Name'],
                        track = track_cache[row['Track']],
                        room = room_cache[room_label],
                        hosts = row['Hosts'],
                        description = row['Conbook Description'],
                    )

                times = row['Room / Time'].split('\n')[0:-1]
                if len(times) == 0:
                    raise Exception('No time information in row {}'.format(row))
                if times[0] in time_map:
                    times = time_map[times[0]]
                for panel_time in times:
                    time_info = time_regex.search(panel_time)
                    if not time_info:
                        raise Exception('Bad time information in row {}'.format(row))
                    time_info = time_info.groupdict()
                    # Special case, make 24:00 into 0:00 midnight
                    if time_info['shour'] == '24':
                        time_info['shour'] = '0'
                    if time_info['ehour'] == '24':
                        time_info['ehour'] = '0'
                    # Add schedule to either panel or room times
                    item.schedule.create(
                        day = time_days[time_info['day']],
                        start_time = time(int(time_info['shour']), int(time_info['sminute'])),
                        end_time = time(int(time_info['ehour']), int(time_info['eminute'])),
                    )
