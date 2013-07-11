from django.conf import settings
import mediasnake

def global_template_variables(request):
    return {'MEDIASNAKE_VERSION': mediasnake.__version__}
