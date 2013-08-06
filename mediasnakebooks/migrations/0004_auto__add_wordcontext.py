# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):
        # Adding model 'WordContext'
        db.create_table(u'mediasnakebooks_wordcontext', (
            (u'id', self.gf('django.db.models.fields.AutoField')(primary_key=True)),
            ('word', self.gf('django.db.models.fields.related.ForeignKey')(to=orm['mediasnakebooks.Word'])),
            ('context', self.gf('django.db.models.fields.TextField')()),
            ('timestamp', self.gf('django.db.models.fields.DateTimeField')(auto_now=True, auto_now_add=True, blank=True)),
        ))
        db.send_create_signal(u'mediasnakebooks', ['WordContext'])


    def backwards(self, orm):
        # Deleting model 'WordContext'
        db.delete_table(u'mediasnakebooks_wordcontext')


    models = {
        u'mediasnakebooks.bookmark': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'Bookmark'},
            'chapter': ('django.db.models.fields.IntegerField', [], {}),
            'ebook': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakebooks.Ebook']", 'unique': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'paragraph': ('django.db.models.fields.IntegerField', [], {}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'})
        },
        u'mediasnakebooks.ebook': {
            'Meta': {'object_name': 'Ebook', 'index_together': "(('author', 'title'),)"},
            'author': ('django.db.models.fields.CharField', [], {'max_length': '128'}),
            'filename': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'title': ('django.db.models.fields.CharField', [], {'max_length': '128'})
        },
        u'mediasnakebooks.language': {
            'Meta': {'object_name': 'Language'},
            'code': ('django.db.models.fields.CharField', [], {'unique': 'True', 'max_length': '3', 'primary_key': 'True'}),
            'dict_url': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'}),
            'stardict': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'mediasnakebooks.word': {
            'Meta': {'unique_together': "(('language', 'base_form'),)", 'object_name': 'Word'},
            'base_form': ('django.db.models.fields.CharField', [], {'max_length': '128', 'db_index': 'True'}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'known': ('django.db.models.fields.IntegerField', [], {'default': '5'}),
            'language': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakebooks.Language']"}),
            'notes': ('django.db.models.fields.TextField', [], {'null': 'True', 'blank': 'True'})
        },
        u'mediasnakebooks.wordcontext': {
            'Meta': {'ordering': "['-timestamp']", 'object_name': 'WordContext'},
            'context': ('django.db.models.fields.TextField', [], {}),
            u'id': ('django.db.models.fields.AutoField', [], {'primary_key': 'True'}),
            'timestamp': ('django.db.models.fields.DateTimeField', [], {'auto_now': 'True', 'auto_now_add': 'True', 'blank': 'True'}),
            'word': ('django.db.models.fields.related.ForeignKey', [], {'to': u"orm['mediasnakebooks.Word']"})
        }
    }

    complete_apps = ['mediasnakebooks']