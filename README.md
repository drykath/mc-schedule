mc-schedule
===========

The mc-schedule app provides the user-facing convention panel and room
schedule for the Motor City Furry Con website.

Live demo: https://motorcityfurrycon.org/schedule/ (Well, usually best
in the spring when the convention is gearing up.)

# Features

* Customizable -- uses standard Django templates/static files.
* Grid and list views -- extend as needed by inheriting the base CBV.
* Filter view by track.
* Past events vanish as the day progresses, showing only the current and future items.
* Past events, when displayed, show a small feedback question.
* Users can mark events and create a customized schedule. Users can mark events as things they don't care to see.
* ICS calendar links -- users can add to a calendar app, like Google Calendar, sync to their phones, set alarms for panels. Updates automatically if the schedule changes.
* Template tag to display upcoming panels on other parts of the site.
* Schedule import (of a specific format, but clone and tune the process as needed.)
* Day transitions other than midnight -- things can be scheduled Saturday, 11 PM to 1 AM.
* Upload map images for each room, and override those where needed for specific events.
* View previous year archived schedules.

# Installation

It requires a Convention parent object, representing the convention year
that the schedule is for. This by default expects to come from the
[mc-convention](https://github.com/drykath/mc-convention) app, but that
can be overridden if you already have a model that represents that. See
the [mc-convention](https://github.com/drykath/mc-convention) docs for
how to set `CONVENTION_MODEL` to something else.

This still uses some other interfaces from that app, so:

    INSTALLED_APPS = [
        ....
        'convention',
        'schedule',
        ....
    ]

And customize the templates/CSS styles as needed. If you use the provided templates make sure the `APP_DIRS` key is enabled in the `TEMPLATES` settings, or just copy or make your own as needed.

## Settings

The app has a few things you can configure in your settings.py:

* `SCHEDULE_IS_PUBLIC`, boolean, self-descriptive.
* `SCHEDULE_DAY_TRANSITION_HOUR` defaults to 4 (4 AM.)
* `SCHEDULE_MEDIA_UPLOAD_TO` as the subdirectory where room/panel map image uploads are stored under the media directory, defaults to 'schedule/'.
* `SCHEDULE_TOKEN_SALT_PREFIX` just in case you want to tinker with the salt used to compute the hash for the customized schedule ICS calendar links.

# Known Issues

There might be some discrepancies whether `USE_TZ` is enabled. Will be testing this more soon.
