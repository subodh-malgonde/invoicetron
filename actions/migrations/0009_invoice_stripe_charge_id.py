# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-23 07:58
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actions', '0008_auto_20170620_1329'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='stripe_charge_id',
            field=models.CharField(blank=True, max_length=100, null=True),
        ),
    ]
