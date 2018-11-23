# -*- coding: utf-8 -*-
# Generated by Django 1.11.14 on 2018-08-26 05:03
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scheduler', '0019_auto_20180826_1431'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduledemailaction',
            name='status',
            field=models.CharField(choices=[('creating', 'Creating'), ('pending', 'Pencding'), ('executing', 'Executing'), ('done', 'Finished'), ('done_error', 'Finished with error')], max_length=256, verbose_name='Execution Status'),
        ),
    ]
