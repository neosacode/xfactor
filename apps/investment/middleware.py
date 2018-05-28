from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.http import HttpResponsePermanentRedirect
from django.conf import settings
from django.core.cache import cache
from django_otp import user_has_device, match_token

from session_security.middleware import SessionSecurityMiddleware

from exchange_core.middleware import UserDocumentsMiddleware
from exchange_core.models import Users, Documents


# Redirects the user if it yet not send the documents
class StepsMiddleware(UserDocumentsMiddleware):
	allowed_paths = [
		reverse('core>documents'),
		reverse('core>settings'),
	]

	def process_request(self, request):
		pass