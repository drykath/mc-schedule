from django.urls import path, re_path

from . import views

urlpatterns = [
    path('', views.ScheduleList.as_view(), name='schedule_default'),
    re_path(r'^grid/(?P<addl_filter>\w*)$', views.ScheduleGrid.as_view(), name='schedule_grid'),
    re_path(r'^list/(?P<addl_filter>\w*)$', views.ScheduleList.as_view(), name='schedule_list'),
    re_path(r'^full/(?P<addl_filter>\w*)$', views.ScheduleFull.as_view(), name='schedule_full'),
    re_path(r'^json/(?P<addl_filter>\w*)@(?P<auth_token>.*)$', views.ScheduleJSON.as_view(), name='schedule_json'),
    re_path(r'^ics/(?P<addl_filter>\w*)@(?P<auth_token>.*)$', views.ScheduleICS.as_view(), name='schedule_ics'),
    path('panel/<int:panelschedule_id>/<slug:slug>', views.panel_detail, name='schedule_panel_detail'),
    path('schedule.css', views.generate_css, name='schedule_css'),
    re_path(r'^setpref/(?P<panel_id>\d+)/(?P<pref>\w*)$', views.set_preference, name='schedule_set_preference'),
]
