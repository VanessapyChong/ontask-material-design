# -*- coding: utf-8 -*-
# Generated by Django 1.11.3 on 2017-12-08 22:47
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dataops', '0005_auto_20171207_1835'),
    ]

    operations = [
        migrations.CreateModel(
            name='PluginRegistry',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('filename', models.CharField(max_length=2048, unique=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256)),
                ('description_txt', models.CharField(blank=True, default='', max_length=65535)),
                ('num_column_input_from', models.IntegerField()),
                ('num_column_input_to', models.IntegerField()),
            ],
        ),
    ]
