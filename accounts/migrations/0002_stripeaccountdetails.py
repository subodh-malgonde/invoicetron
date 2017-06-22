# -*- coding: utf-8 -*-
# Generated by Django 1.9.6 on 2017-06-22 05:48
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='StripeAccountDetails',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('stripe_user_id', models.CharField(max_length=100)),
                ('stripe_publish_key', models.CharField(max_length=100)),
                ('stripe_access_token', models.CharField(max_length=100)),
                ('team', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='accounts.Team')),
            ],
        ),
    ]
