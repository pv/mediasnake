# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Bookmark',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('page', models.IntegerField()),
                ('timestamp', models.DateTimeField(auto_now=True, auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Comic',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filename', models.TextField()),
                ('title', models.CharField(max_length=128)),
                ('path', models.CharField(max_length=128)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.AlterIndexTogether(
            name='comic',
            index_together=set([('path', 'title')]),
        ),
        migrations.AddField(
            model_name='bookmark',
            name='comic',
            field=models.ForeignKey(to='mediasnakecomics.Comic', unique=True),
            preserve_default=True,
        ),
    ]
