# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('third_party_auth', '0005_add_site_field'),
    ]

    operations = [
        migrations.AddField(
            model_name='samlproviderconfig',
            name='identity_provider_type',
            field=models.CharField(default=b'standard_saml', help_text=b'If using an identity provider with specific behavioral needs, set here.', max_length=128, verbose_name=b'Identity Provider Type', choices=[(b'standard_saml', b'Standard SAML provider'), (b'sap_success_factors', b'SAP SuccessFactors provider')]),
        ),
    ]
