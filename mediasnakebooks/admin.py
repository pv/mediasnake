from django.contrib import admin
from mediasnakebooks.models import Language

class LanguageAdmin(admin.ModelAdmin):
    fields = ('code', 'stardict', 'dict_url')

admin.site.register(Language, LanguageAdmin)
