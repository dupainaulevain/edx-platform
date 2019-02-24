"""
Views to show announcements.
"""

from django.conf import settings
from django.http import JsonResponse
from django.views.generic.list import ListView

from .models import Announcement


class AnnouncementsJSONView(ListView):
    """
    View returning a page of announcements for the dashboard
    """
    model = Announcement
    object_list = Announcement.objects.filter(active=True)
    paginate_by = settings.FEATURES.get('ANNOUNCEMENTS_PER_PAGE', 3)

    def get(self, request, *args, **kwargs):
        """
        Return active announcements as json
        """
        context = self.get_context_data()

        announcements = [{"content": announcement.content} for announcement in context['object_list']]
        result = {
            "announcements": announcements,
            "next": context['page_obj'].has_next(),
            "prev": context['page_obj'].has_previous(),
            "num_pages": context['paginator'].num_pages,
        }
        return JsonResponse(result)
