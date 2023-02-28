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
            else:
                if not options['append']:
                    raise CommandError('Convention already has panels, cannot import without --append or --clear')

        # Cache the Room and Track objects by name
        rooms = Room.objects.filter(convention=convention)
        room_cache = {room.name: room for room in rooms}
        # If the room is called a different thing, or has a specific purpose
        room_cache.update({room.alias: room for room in rooms if room.alias})
        # Upper case versions to match CSV export
        room_cache.update({room.name.upper(): room for room in rooms})
        room_cache.update({room.alias.upper(): room for room in rooms if room.alias})

        tracks = Track.objects.filter(convention=convention)
        track_cache = {track.name: track for track in tracks}

        # Maps to correct shortcuts in the source data
        time_map = {
            'ALWAYS OPEN': ['THU: 1800-0030', 'FRI: 0900-0200', 'SAT: 0900-0200', 'SUN: 0900-0200'],
        }
        time_regex = re.compile('^(?P<day>\w{3}): (?P<shour>\d{2})(?P<sminute>\d{2})-(?P<ehour>\d{2})(?P<eminute>\d{2})\s*$')
        time_days = {
            'THURSDAY': 3,
            'FRIDAY': 4,
            'SATURDAY': 5,
            'SUNDAY': 6,
        }

        line = 1
        with open(options['csv_path'], 'r') as schedulefile:
            for row in csv.DictReader(schedulefile):
                line += 1
                # Ignore room times, this year these seem complex enough that it's easier to enter manually than parse
                if row['Panel Name'] in (
                            "",
                            "Panel Name",
                            "Fursuit Headless Lounge",
                            "Artist Quiet Area",
                            "Artist's Alley Sign Up",
                            "Registration - Pre-reg Only",
                            "Registration",
                            "Video Game Room",
                            "Con Store",
                            "Con Store - Pre-Reg Swag Pick Up",
                            "Tabletop Gaming",
                            "Artist's Alley",
                            "Dealer's Den",
                            "Sponsor's Lounge",
                            "Fursuit Dance Prelims", # Remember to add that one in manually, too
                            "Vintage Fursuits", # Remember to add that one in manually, too
                        ) or row['Panel Name'].startswith('Fuzzy Logic'):
                    continue
                if 'Exclude' in row and row['Exclude'] == 'Yes':
                    continue

                # Map rooms and times
                room_label = row['ROOM']
                track_label = row['Track']
                if track_label == '':
                    track_label = 'Other'

                if not room_label in room_cache:
                    raise Exception('Room "{}" unknown on line {}'.format(room_label, line))
                if not track_label in track_cache:
                    raise Exception('Track "{}" unknown on line {}'.format(track_label, line))

                if debug:
                    print(row)
                if row['Panel Name'] in room_cache.keys():
                    item = room_cache[row['Panel Name']]
                else:
                    item = Panel.objects.create(
                        convention = convention,
                        title = row['Panel Name'],
                        track = track_cache[track_label],
                        room = room_cache[room_label],
                        hosts = row['Hosts'],
                        description = row['Conbook Description'],
                    )

                #if times[0] in time_map:
                #    times = time_map[times[0]]
                #for panel_time in times:
                start_time = datetime.strptime(row['Start Time'], "%I:%M %p").time()
                end_time = datetime.strptime(row['End Time'], "%I:%M %p").time()
                # Add schedule to either panel or room times
                item.schedule.create(
                    day = time_days[row['Day'].upper()],
                    start_time = start_time,
                    end_time = end_time,
                )
