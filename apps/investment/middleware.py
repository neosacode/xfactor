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
		if user_has_device(request.user):
			return
		if self.must_ignore(request):
			return
		if not request.user.is_authenticated:
			return

		cache.clear()
		profile_data = Users.objects.get(pk=request.user.pk).profile
		documents_qty = request.user.documents.count()
		settings_is_not_ok = (not 'has_personal' in profile_data or not 'has_address' in profile_data)


		if settings_is_not_ok and not request.path.startswith(reverse('core>settings')):
			return HttpResponsePermanentRedirect(reverse('core>settings'))
		if not settings_is_not_ok and documents_qty < 4 and not request.path.startswith(reverse('core>documents')):
			return HttpResponsePermanentRedirect(reverse('core>documents'))
		if 'has_personal' in profile_data and 'has_address' in profile_data \
				and not request.path.startswith(reverse('two_factor:profile')) \
				and not user_has_device(request.user):
			return HttpResponsePermanentRedirect(reverse('two_factor:profile'))
