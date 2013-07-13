from django.conf import settings
import mediasnake

def global_template_variables(request):
    return {
        'MEDIASNAKE_VERSION': mediasnake.__version__,
        'GLOBAL_VIDEO_DIRS': settings.MEDIASNAKEFILES_DIRS,
        }
