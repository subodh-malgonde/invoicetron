# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-16 10:47
from __future__ import unicode_literals
import datetime
from django.utils.timezone import utc
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('actions', '0005_auto_20170616_0547'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=datetime.datetime(2017, 6, 16, 6, 39, 13, 70499, tzinfo=utc)),
            preserve_default=False,
        ),
    ]