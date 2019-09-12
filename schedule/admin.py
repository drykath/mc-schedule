from django.contrib import admin

from convention import get_convention_model
from convention.admin import ConventionListFilter

from .models import Panel, PanelSchedule, Attendee, Room, RoomSchedule, Track

Convention = get_convention_model()

class PanelScheduleInline(admin.TabularInline):
    model = PanelSchedule
    extra = 1
    exclude = ['start_timestamp', 'end_timestamp']


class PanelAttendeesInline(admin.TabularInline):
    model = Attendee
    can_delete = False
    extra = 0
    max_num = 0
    fields = ['attended', 'feedback']
    readonly_fields = ['attended', 'feedback']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        return queryset.exclude(feedback=None)


class PanelAdmin(admin.ModelAdmin):
    list_display = ('title', 'track', 'room')
    list_filter = (ConventionListFilter, 'track', 'room', 'schedule__day')
    search_fields = ['title', 'hosts', 'description', 'notes']
    inlines = [PanelScheduleInline, PanelAttendeesInline]

    filter_convention = None

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.filter_convention = obj.convention
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self.filter_convention:
            if db_field.name == 'track':
                kwargs['queryset'] = Track.objects.filter(convention=self.filter_convention)
            if db_field.name == 'room':
                kwargs['queryset'] = Room.objects.filter(convention=self.filter_convention)
        else:
            if db_field.name == 'track':
                kwargs['queryset'] = Track.objects.filter(convention=Convention.objects.current())
            if db_field.name == 'room':
                kwargs['queryset'] = Room.objects.filter(convention=Convention.objects.current())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Panel, PanelAdmin)


class RoomScheduleInline(admin.TabularInline):
    model = RoomSchedule
    extra = 1
    exclude = ['start_timestamp', 'end_timestamp']


class RoomAdmin(admin.ModelAdmin):
    list_display = ('name', 'alias', 'sort_order')
    list_filter = (ConventionListFilter,)
    search_fields = ['name', 'alias']
    inlines = [RoomScheduleInline]

    filter_convention = None

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            self.filter_convention = obj.convention
        return super().get_form(request, obj, **kwargs)

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        if self.filter_convention:
            if db_field.name == 'track':
                kwargs['queryset'] = Track.objects.filter(convention=self.filter_convention)
        else:
            if db_field.name == 'track':
                kwargs['queryset'] = Track.objects.filter(convention=Convention.objects.current())
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


admin.site.register(Room, RoomAdmin)


class TrackAdmin(admin.ModelAdmin):
    list_display = ('name', 'color')
    list_filter = (ConventionListFilter,)
    search_fields = ['name', 'color', 'class_name']


admin.site.register(Track, TrackAdmin)
