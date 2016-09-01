# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('course_overviews', '0009_readd_facebook_url'),
    ]

    operations = [
        migrations.AddField(
            model_name='courseoverview',
            name='self_paced',
            field=models.BooleanField(default=False),
        ),
    ]
