# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-19 07:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('action', '0034_auto_20180819_1645'),
    ]

    operations = [
        migrations.AddField(
            model_name='action',
            name='last_executed',
            field=models.DateTimeField(blank=True, null=True, verbose_name='Last execution'),
        ),
    ]
