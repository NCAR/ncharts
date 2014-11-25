
from django.conf import settings
from django.core.urlresolvers import reverse, NoReverseMatch
# from django.http import Http404
import django.core.exceptions


import logging
logger = logging.getLogger(__name__)

class InternalUseOnlyMiddleware(object):
    """
    Middleware to prevent access to the admin if the user IP
    isn't in the INTERNAL_IPS setting.
    """
    def process_request(self, request):
        # logger.debug("InternalUseOnlyMiddlewarem process_request")
        try:
            admin_index = reverse('admin:index')
        except NoReverseMatch:
            return
        if not request.path.startswith(admin_index):
            return
        remote_addr = request.META.get(
            'HTTP_X_REAL_IP', request.META.get('REMOTE_ADDR', None))
        # logger.debug("request.path=%s, remote_addr=%s",request.path,remote_addr)
        for ip in settings.INTERNAL_IPS:
            if remote_addr.startswith(ip):
                return
        logger.warning("attempt to use admin site from unauthorized IP: %s",remote_addr)
        raise django.core.exceptions.PermissionDenied
