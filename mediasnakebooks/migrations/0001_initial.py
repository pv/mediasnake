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
                ('chapter', models.IntegerField()),
                ('paragraph', models.IntegerField()),
                ('timestamp', models.DateTimeField(auto_now=True, auto_now_add=True)),
            ],
            options={
                'ordering': ['-timestamp'],
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Ebook',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('filename', models.TextField()),
                ('title', models.CharField(max_length=128)),
                ('author', models.CharField(max_length=128)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Language',
            fields=[
                ('code', models.CharField(help_text=b'3-letter ISO language code', max_length=3, unique=True, serialize=False, primary_key=True)),
                ('stardict', models.TextField(help_text=b'Full file name of a Stardict format dictionary (on the server)', null=True, blank=True)),
                ('dict_url', models.TextField(help_text=b'Dictionary URL: @WORD@ is replaced by the word to search for', null=True, blank=True)),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='Word',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('base_form', models.CharField(help_text=b'Base form of the word', max_length=128, db_index=True)),
                ('notes', models.TextField(null=True, blank=True)),
                ('known', models.IntegerField(default=5, help_text=b'Knowledge level: 5 - unknown, ..., 1 - well known, 0 - ignored')),
                ('language', models.ForeignKey(to='mediasnakebooks.Language')),
            ],
            options={
            },
            bases=(models.Model,),
        ),
        migrations.CreateModel(
            name='WordContext',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('context', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now=True, auto_now_add=True)),
                ('word', models.ForeignKey(to='mediasnakebooks.Word')),
            ],
            options={
                'ordering': ['-timestamp'],
            },
            bases=(models.Model,),
        ),
        migrations.AlterUniqueTogether(
            name='word',
            unique_together=set([('language', 'base_form')]),
        ),
        migrations.AlterIndexTogether(
            name='ebook',
            index_together=set([('author', 'title')]),
        ),
        migrations.AddField(
            model_name='bookmark',
            name='ebook',
            field=models.ForeignKey(to='mediasnakebooks.Ebook', unique=True),
            preserve_default=True,
        ),
    ]
