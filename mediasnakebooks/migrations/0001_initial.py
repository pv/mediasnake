# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'Language'
        db.create_table(u'mediasnakebooks_language', (
            ('code', self.gf('django.db.models.fields.CharField')(unique=True, max_length=3, primary_key=True)),
            ('stardict', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('dict_url', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Language'])

        # Adding model 'Word'
        db.create_table(u'mediasnakebooks_word', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('language', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mediasnakebooks.Language'])),
            ('base_form', self.gf('django.db.models.fields.CharField')(max_length=128)),
            ('notes', self.gf('django.db.models.fields.TextField')(null=True, blank=True)),
            ('known', self.gf('django.db.models.fields.IntegerField')(default=5)),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Word'])

        # Adding unique constraint on 'Word', fields ['language', 'base_form']
        db.create_unique(u'mediasnakebooks_word', ['language_id', 'base_form'])

        # Adding model 'Ebook'
        db.create_table(u'mediasnakebooks_ebook', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('filename', self.gf('django.db.models.fields.TextField')()),
            ('title', self.gf('django.db.models.fields.TextField')()),
            ('author', self.gf('django.db.models.fields.TextField')()),
        ))
        db.send_create_signal(u'mediasnakebooks', ['Ebook'])


    def backwards(self, orm):
        # Removing unique constraint on 'Word', fields ['language', 'base_form']
        db.delete_unique(u'mediasnakebooks_word', ['language_id', 'base_form'])

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
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3', 'primary_key': 'True'}),
            'dict_url': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'stardict': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'mediasnakebooks.word': {
            'Meta': {'unique_together': "(('language', 'base_form'),)", 'object_name': 'Word'},
            'base_form': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'known': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakebooks.Language']"}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        }
    }

    complete_apps = ['mediasnakebooks']