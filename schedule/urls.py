from django.conf.urls import url

from . import views

urlpatterns = [
    url(r'^$', views.ScheduleList.as_view(), name='schedule_default'),
    url(r'^grid/(?P<addl_filter>\w*)$', views.ScheduleGrid.as_view(), name='schedule_grid'),
    url(r'^list/(?P<addl_filter>\w*)$', views.ScheduleList.as_view(), name='schedule_list'),
    url(r'^json/(?P<addl_filter>\w*)@(?P<auth_token>.*)$', views.ScheduleJSON.as_view(), name='schedule_json'),
    url(r'^ics/(?P<addl_filter>\w*)@(?P<auth_token>.*)$', views.ScheduleICS.as_view(), name='schedule_ics'),
    url(r'^panel/(?P<panelschedule_id>\d+)/(?P<slug>[-\w]*)$', views.panel_detail, name='schedule_panel_detail'),
    url(r'^schedule\.css$', views.generate_css, name='schedule_css'),
    url(r'^setpref/(?P<panel_id>\d+)/(?P<pref>\w*)$', views.set_preference, name='schedule_set_preference'),
]
