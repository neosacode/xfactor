from django.utils.deprecation import MiddlewareMixin
from django.urls import reverse
from django.http import HttpResponsePermanentRedirect
from django.conf import settings
from django_otp import user_has_device, match_token

from session_security.middleware import SessionSecurityMiddleware

from exchange_core.middleware import UserDocumentsMiddleware
from exchange_core.models import Users, Documents


# Redirects the user if it yet not send the documents
class StepsMiddleware(UserDocumentsMiddleware):
	def process_request(self, request):
		if self.must_ignore(request):
			return
		if not request.user.is_authenticated or user_has_device(request.user):
			return

		profile_data = request.user.profile
		documents_qty = request.user.documents.count()

		if documents_qty < 4 not in profile_data and not request.path.startswith(reverse('core>documents')):
			return HttpResponsePermanentRedirect(reverse('core>documents'))
		if documents_qty >= 4 and (not 'has_personal' in profile_data
				or not 'has_address' in profile_data) \
				and not request.path.startswith(reverse('core>settings')):
			return HttpResponsePermanentRedirect(reverse('core>settings'))
		if 'has_personal' in profile_data and 'has_address' in profile_data \
				and not request.path.startswith(reverse('two_factor:profile')):
			return HttpResponsePermanentRedirect(reverse('two_factor:profile'))

