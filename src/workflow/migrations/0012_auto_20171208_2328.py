# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-08 12:28
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('workflow', '0011_auto_20171208_2327'),
    ]

    operations = [
        migrations.AlterField(
            model_name='column',
            name='valid_from',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Column valid from'),
        ),
        migrations.AlterField(
            model_name='column',
            name='valid_to',
            field=models.DateTimeField(blank=True, default=None, null=True, verbose_name='Column valid until'),
        ),
    ]
