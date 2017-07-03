# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-29 07:27
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('landing', '0004_auto_20170626_0731'),
    ]

    operations = [
        migrations.AlterField(
            model_name='userinteractionstate',
            name='state',
            field=models.CharField(choices=[('chilling', 'Chilling'), ('line_item_description_awaited', 'Line item description awaited'), ('line_item_amount_awaited', 'Line item amount awaited'), ('line_item_for_the_first_time', 'Line item description for the first time'), ('company_name_awaited', 'Company name for the invoice'), ('client_name_awaited', 'Client name awaited for editing'), ('client_email_awaited', 'Client email awaited for editing')], default='chilling', max_length=50),
        ),
    ]