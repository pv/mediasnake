from django.contrib import admin
from mediasnakebooks.models import Language, Word

class LanguageAdmin(admin.ModelAdmin):
    fields = ('code', 'stardict', 'dict_url')

class WordAdmin(admin.ModelAdmin):
    fields = ('language', 'base_form', 'notes', 'known')

admin.site.register(Language, LanguageAdmin)
admin.site.register(Word, WordAdmin)
