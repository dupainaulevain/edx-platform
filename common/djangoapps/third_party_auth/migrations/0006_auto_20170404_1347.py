# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party_auth', '0005_add_site_field'),
    ]

    operations = [
        migrations.AlterField(
            model_name='samlproviderconfig',
            name='other_settings',
            field=models.TextField(help_text=b'For advanced use cases, enter a JSON object with addtional configuration. The tpa-saml backend supports only {"requiredEntitlements": ["urn:..."]} which can be used to require the presence of a specific eduPersonEntitlement. Other provider types, as selected in the "backend name" field, may make use of additional information stored in this field for configuration.', verbose_name=b'Advanced settings', blank=True),
        ),
    ]
