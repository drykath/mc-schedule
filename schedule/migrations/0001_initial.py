from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        #('convention', '0001_initial'),
        migrations.swappable_dependency(getattr(settings, 'CONVENTION_MODEL', 'convention.Convention')),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Attendee',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('starred', models.BooleanField(default=False)),
                ('hide_from_user', models.BooleanField(default=False)),
                ('attended', models.NullBooleanField()),
                ('feedback', models.TextField(blank=True, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='Panel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=255)),
                ('hosts', models.TextField(max_length=255)),
                ('hidden', models.BooleanField(default=False)),
                ('description', models.TextField(blank=True, null=True)),
                ('notes', models.TextField(blank=True, null=True)),
                ('map_image', models.FileField(blank=True, null=True, upload_to='schedule/')),
                ('attendees', models.ManyToManyField(through='schedule.Attendee', to=settings.AUTH_USER_MODEL)),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=getattr(settings, 'CONVENTION_MODEL', 'convention.Convention'))),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('alias', models.CharField(blank=True, max_length=255, null=True)),
                ('description', models.TextField(blank=True, help_text='Only needed if this room has open/close times', null=True, verbose_name='description on schedule')),
                ('sort_order', models.IntegerField(blank=True, null=True)),
                ('location_hint', models.CharField(blank=True, max_length=255, null=True)),
                ('always_open', models.BooleanField(default=False)),
                ('map_image', models.FileField(blank=True, null=True, upload_to='schedule/')),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=getattr(settings, 'CONVENTION_MODEL', 'convention.Convention'))),
            ],
            options={
                'ordering': ['convention', 'sort_order'],
            },
        ),
        migrations.CreateModel(
            name='Track',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100)),
                ('class_name', models.CharField(max_length=25)),
                ('color', models.CharField(max_length=10)),
                ('convention', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=getattr(settings, 'CONVENTION_MODEL', 'convention.Convention'))),
            ],
            options={
                'ordering': ['convention', 'name'],
                'unique_together': {('convention', 'class_name'), ('convention', 'name')},
            },
        ),
        migrations.CreateModel(
            name='RoomSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.IntegerField(choices=[(3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'), (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule', to='schedule.Room')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='room',
            name='track',
            field=models.ForeignKey(blank=True, help_text='Only needed if this room has open/close times', null=True, on_delete=django.db.models.deletion.PROTECT, to='schedule.Track'),
        ),
        migrations.CreateModel(
            name='PanelSchedule',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('day', models.IntegerField(choices=[(3, 'Thursday'), (4, 'Friday'), (5, 'Saturday'), (6, 'Sunday'), (0, 'Monday'), (1, 'Tuesday'), (2, 'Wednesday')])),
                ('start_time', models.TimeField()),
                ('end_time', models.TimeField()),
                ('panel', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='schedule', to='schedule.Panel')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.AddField(
            model_name='panel',
            name='room',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='schedule.Room'),
        ),
        migrations.AddField(
            model_name='panel',
            name='track',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='schedule.Track'),
        ),
        migrations.AddField(
            model_name='attendee',
            name='panel',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to='schedule.Panel'),
        ),
        migrations.AddField(
            model_name='attendee',
            name='user',
            field=models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterUniqueTogether(
            name='room',
            unique_together={('convention', 'name')},
        ),
        migrations.AlterUniqueTogether(
            name='attendee',
            unique_together={('user', 'panel')},
        ),
    ]
