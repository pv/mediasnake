from django.http import HttpResponseForbidden
from mediasnakefiles.views import ticket_stream

class SSLEnforcer(object):
    """
    Allow non-SSL access only to the /ticket/ URLs.
    """

    def process_view(self, request, view_func, view_args, view_kwargs):
        if view_func is not ticket_stream:
            if not request.is_secure():
                return HttpResponseForbidden('403 Forbidden')
        return None
