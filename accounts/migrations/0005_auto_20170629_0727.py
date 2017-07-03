# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-29 07:27
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0004_company_company_logo'),
    ]

    operations = [
        migrations.AddField(
            model_name='customer',
            name='edited_details_awaited_from',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='accounts.Employee'),
        ),
        migrations.AlterField(
            model_name='customer',
            name='created_by',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='created_customers', to='accounts.Employee'),
        ),
    ]