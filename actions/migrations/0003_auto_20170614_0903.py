# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-14 09:03
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('actions', '0002_auto_20170614_0706'),
    ]

    operations = [
        migrations.AlterField(
            model_name='lineitem',
            name='invoice',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='line_items', to='actions.Invoice'),
        ),
    ]
