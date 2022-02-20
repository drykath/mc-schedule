# Django is deprecating the NullBooleanField, so this migration and code
# change works around that. It should be a database no-op.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('schedule', '0003_move_convention_model'),
    ]

    operations = [
        migrations.AlterField(
            model_name='attendee',
            name='attended',
            field=models.BooleanField(null=True),
        ),
    ]
