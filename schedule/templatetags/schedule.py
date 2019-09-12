from django import template
from django.db.models import Prefetch
from django.utils import timezone
from convention import get_convention_model

from ..models import Attendee, PanelSchedule

Convention = get_convention_model()

register = template.Library()

@register.inclusion_tag('schedule/upcoming_panels.html')
def upcoming_panels(addl_filter='', limit=5, include_current=True, user=None):
    '''
    Display a list of upcoming panels on any page.
    '''

    # TODO: Consider eventually leveraging views.Schedule

    if addl_filter not in ['', 'custom', 'all']:
        raise template.TemplateSyntaxError(
            "upcoming_panels tag addl_filter must be one of '', 'custom', or 'all'"
        )
    if addl_filter == 'custom' and (not user or not user.is_authenticated):
        raise template.TemplateSyntaxError(
            "upcoming_panels tag addl_filter='custom' must receive a logged in user"
        )

    convention = Convention.objects.current()
    if not convention:
        return {}
    now = timezone.now().replace(tzinfo=timezone.get_current_timezone())

    # Determine query based on the parameters
    panelschedules = PanelSchedule.objects.select_related(
        'panel', 'panel__room'
    ).filter(
        panel__convention=convention, panel__hidden=False
    ).order_by('day')

    if addl_filter != 'all':
        # Filter our not-all views by date, and later time, if the convention has started
        if convention.start_date < timezone.now().date():
            panelschedules = panelschedules.exclude(
                day__lt=convention.start_date.weekday())

        # Apply additional filtering if the user has logged in
        if user.is_authenticated:
            if addl_filter == '':
                panelschedules = panelschedules.exclude(
                    panel__attendee__in=Attendee.objects.filter(
                        user=user, hide_from_user=True))
            if addl_filter == 'custom':
                panelschedules = panelschedules.filter(
                    panel__attendee__user=user, panel__attendee__starred=True)

    if user.is_authenticated:
        # Pre-fetch any preference records for this attendee
        panelschedules = panelschedules.prefetch_related(
            Prefetch('panel__attendee_set',
                     queryset=Attendee.objects.filter(user=user),
                     to_attr='attendee_info'))

    # Filter panelschedules by time, and then put in proper time order
    filtered_panelschedules = [ps for ps in panelschedules if
        ps.start_timestamp > now or (include_current and ps.end_timestamp > now)
    ]
    filtered_panelschedules.sort(key=lambda ps: ps.start_timestamp)

    if limit:
        filtered_panelschedules = filtered_panelschedules[:limit]

    return {'panelschedules': filtered_panelschedules}
