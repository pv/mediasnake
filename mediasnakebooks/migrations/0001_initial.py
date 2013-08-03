# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Language'
        db.create_table(u'mediasnakebooks_language', (
            ('code', self.gf('django.db.models.fields.CharField')(max_length=3, primary_key=True)),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Language'])

        # Adding model 'Word'
        db.create_table(u'mediasnakebooks_word', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('language', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mediasnakebooks.Language'])),
            ('base_form', self.gf('django.db.models.fields.TextField')()),
            ('alt_form', self.gf('django.db.models.fields.TextField')(null=True)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True)),
            ('known', self.gf('django.db.models.fields.IntegerField')(default=5)),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Word'])

        # Adding model 'Ebook'
        db.create_table(u'mediasnakebooks_ebook', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.TextField')()),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('author', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Ebook'])


    def backwards(self, orm):
        # Deleting model 'Language'
        db.delete_table(u'mediasnakebooks_language')

        # Deleting model 'Word'
        db.delete_table(u'mediasnakebooks_word')

        # Deleting model 'Ebook'
        db.delete_table(u'mediasnakebooks_ebook')


    models = {
        u'mediasnakebooks.ebook': {
            'Meta': {'object_name': 'Ebook'},
            'author': ('django.db.models.fields.TextField', [], {}),
            'filename': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.TextField', [], {})
        },
        u'mediasnakebooks.language': {
            'Meta': {'object_name': 'Language'},
            'code': ('django.db.models.fields.CharField', [], {'max_length': '3', 'primary_key': 'True'})
        },
        u'mediasnakebooks.word': {
            'Meta': {'object_name': 'Word'},
            'alt_form': ('django.db.models.fields.TextField', [], {'null': 'True'}),
            'base_form': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'known': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakebooks.Language']"}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True'})
        }
    }

    complete_apps = ['mediasnakebooks']