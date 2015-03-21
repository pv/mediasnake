# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='StreamingTicket',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('secret', models.CharField(unique=True, max_length=128)),
                ('timestamp', models.DateTimeField()),
                ('remote_address', models.IPAddressField()),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='VideoFile',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filename', models.TextField()),
                ('mimetype', models.CharField(max_length=256)),
                ('thumbnail', models.CharField(max_length=256)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AddField(
            model_name='streamingticket',
            name='video_file',
            field=models.ForeignKey(to='mediasnakefiles.VideoFile'),
            preserve_default=True,
        ),
    ]
