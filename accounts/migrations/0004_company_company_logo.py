# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-29 05:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0003_auto_20170626_0731'),
    ]

    operations = [
        migrations.AddField(
            model_name='company',
            name='company_logo',
            field=models.ImageField(blank=True, null=True, upload_to=''),
        ),
    ]
