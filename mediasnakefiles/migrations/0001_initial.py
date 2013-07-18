# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'VideoFile'
        db.create_table(u'mediasnakefiles_videofile', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.TextField')()),
            ('mimetype', self.gf('django.db.models.fields.CharField')(max_length=256)),
            ('thumbnail', self.gf('django.db.models.fields.CharField')(max_length=256)),
        ))
        db.send_create_signal(u'mediasnakefiles', ['VideoFile'])

        # Adding model 'StreamingTicket'
        db.create_table(u'mediasnakefiles_streamingticket', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('secret', self.gf('django.db.models.fields.CharField')(unique=True, max_length=128)),
            ('video_file', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mediasnakefiles.VideoFile'])),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')()),
            ('remote_address', self.gf('django.db.models.fields.IPAddressField')(max_length=15)),
        ))
        db.send_create_signal(u'mediasnakefiles', ['StreamingTicket'])


    def backwards(self, orm):
        # Deleting model 'VideoFile'
        db.delete_table(u'mediasnakefiles_videofile')

        # Deleting model 'StreamingTicket'
        db.delete_table(u'mediasnakefiles_streamingticket')


    models = {
        u'mediasnakefiles.streamingticket': {
            'Meta': {'object_name': 'StreamingTicket'},
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'remote_address': ('django.db.models.fields.IPAddressField', [], {'max_length': '15'}),
            'secret': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '128'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {}),
            'video_file': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakefiles.VideoFile']"})
        },
        u'mediasnakefiles.videofile': {
            'Meta': {'object_name': 'VideoFile'},
            'filename': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'mimetype': ('django.db.models.fields.CharField', [], {'max_length': '256'}),
            'thumbnail': ('django.db.models.fields.CharField', [], {'max_length': '256'})
        }
    }

    complete_apps = ['mediasnakefiles']