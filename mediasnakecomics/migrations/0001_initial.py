# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Comic'
        db.create_table(u'mediasnakecomics_comic', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.TextField')()),
            ('title', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('path', self.gf('django.db.models.fields.CharField')(max_length=128)),
        ))
        db.send_create_signal(u'mediasnakecomics', ['Comic'])

        # Adding index on 'Comic', fields ['path', 'title']
        db.create_index(u'mediasnakecomics_comic', ['path', 'title'])

        # Adding model 'Bookmark'
        db.create_table(u'mediasnakecomics_bookmark', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('comic', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mediasnakecomics.Comic'], unique=True)),
            ('page', self.gf('django.db.models.fields.IntegerField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'mediasnakecomics', ['Bookmark'])


    def backwards(self, orm):
        # Removing index on 'Comic', fields ['path', 'title']
        db.delete_index(u'mediasnakecomics_comic', ['path', 'title'])

        # Deleting model 'Comic'
        db.delete_table(u'mediasnakecomics_comic')

        # Deleting model 'Bookmark'
        db.delete_table(u'mediasnakecomics_bookmark')


    models = {
        u'mediasnakecomics.bookmark': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Bookmark'},
            'comic': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakecomics.Comic']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'page': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'})
        },
        u'mediasnakecomics.comic': {
            'Meta': {'object_name': 'Comic', 'index_together': "(('path', 'title'),)"},
            'filename': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'path': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        }
    }

    complete_apps = ['mediasnakecomics']