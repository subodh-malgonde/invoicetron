# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-26 07:31
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0003_auto_20170619_1027'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinteractionstate',
            name='state',
            field=models.CharField(choices=[('chilling', 'Chilling'), ('line_item_description_awaited', 'Line item description awaited'), ('line_item_amount_awaited', 'Line item amount awaited'), ('line_item_for_the_first_time', 'Line item description for the first time'), ('company_name_awaited', 'Company name for the invoice')], default='chilling', max_length=50),
        ),
    ]
