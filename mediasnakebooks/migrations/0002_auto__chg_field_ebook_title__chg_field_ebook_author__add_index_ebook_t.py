# -*- coding: utf-8 -*-
import datetime
from south.db import db
from south.v2 import SchemaMigration
from django.db import models


class Migration(SchemaMigration):

    def forwards(self, orm):

        # Changing field 'Ebook.title'
        db.alter_column(u'mediasnakebooks_ebook', 'title', self.gf('django.db.models.fields.CharField')(max_length=128))

        # Changing field 'Ebook.author'
        db.alter_column(u'mediasnakebooks_ebook', 'author', self.gf('django.db.models.fields.CharField')(max_length=128))
        # Adding index on 'Ebook', fields ['author', 'title']
        db.create_index(u'mediasnakebooks_ebook', ['author', 'title'])

        # Adding index on 'Word', fields ['base_form']
        db.create_index(u'mediasnakebooks_word', ['base_form'])


    def backwards(self, orm):
        # Removing index on 'Word', fields ['base_form']
        db.delete_index(u'mediasnakebooks_word', ['base_form'])

        # Removing index on 'Ebook', fields ['title', 'author']
        db.delete_index(u'mediasnakebooks_ebook', ['author', 'title'])


        # Changing field 'Ebook.title'
        db.alter_column(u'mediasnakebooks_ebook', 'title', self.gf('django.db.models.fields.TextField')())

        # Changing field 'Ebook.author'
        db.alter_column(u'mediasnakebooks_ebook', 'author', self.gf('django.db.models.fields.TextField')())

    models = {
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
        }
    }

    complete_apps = ['mediasnakebooks']
