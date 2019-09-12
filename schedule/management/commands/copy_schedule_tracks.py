from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from schedule.models import Room, Track
# TODO: Need to abstract this link still...
from convention.models import Convention

class Command(BaseCommand):
    help = 'Duplicate the Room and Track objects from another Convention'

    def add_arguments(self, parser):
        parser.add_argument('from_convention', type=str)

        parser.add_argument(
            '--clear',
            action='store_true',
            dest='clear',
            default=False,
            help='Removal all room and track items from the new convention before copy'
        )

    @transaction.atomic
    def handle(self, *args, **options):
        convention = Convention.objects.current()

        # If given a number, try that as the convention id. Otherwise, look up by name.
        # And just fail out if we don't get a match.
        try:
            old_convention = Convention.objects.get(id=int(options['from_convention']))
        except ValueError:
            old_convention = Convention.objects.get(name=options['from_convention'])

        if convention == old_convention:
            raise CommandError('Convention "{}" is the destination, cannot use as the source'.format(convention.name))

        existing = Track.objects.filter(convention=convention)
        if len(existing) > 0:
            if options['clear']:
                existing.delete()
                Room.objects.filter(convention=convention).delete()
            else:
                raise CommandError('Convention already has tracks, cannot copy without --clear')

        # Duplicate the Track and Room objects, reassigning to the new convention
        for track in Track.objects.filter(convention=old_convention):
            track.pk = None
            track.convention = convention
            track.save()

        for room in Room.objects.filter(convention=old_convention):
            room.pk = None
            room.convention = convention
            room.save()
