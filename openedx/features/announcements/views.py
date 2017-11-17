"""
Views to show announcements.
"""

from django.conf import settings
from django.http import JsonResponse, HttpResponseRedirect
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.utils.translation import ugettext as _
from django.template.loader import render_to_string
from django.core.urlresolvers import reverse, reverse_lazy
from web_fragments.fragment import Fragment

from openedx.core.djangoapps.plugin_api.views import EdxFragmentView

from .models import Announcement


class AnnouncementsView(EdxFragmentView, ListView):
    """
    View showing a list of all announcements.
    """
    model = Announcement
    object_list = Announcement.objects.all()
    context_object_name = 'announcement_list'
    template_name = "announcements/announcements_list.html"
    paginate_by = settings.FEATURES.get('ANNOUNCEMENTS_PER_PAGE', 3)

    def render_to_fragment(self, request, **kwargs):
        """
        Render page which lists all announcements
        """
        if "limit" in request.GET.keys():
            self.paginate_by = request.GET.get("limit")
        html = render_to_string(self.template_name, self.get_context_data(), request=request)
        return Fragment(html)


class AnnouncementEditView(EdxFragmentView):
    """
    View to edit an announcement.
    """
    template_name = "announcements/announcements_edit.html"

    def render_to_fragment(self, request, **kwargs):
        """
        Show Announcement edit form
        """
        announcement = Announcement.objects.filter(pk=kwargs.get('pk')).first()
        context = {
            "announcement": announcement
        }
        html = render_to_string(self.template_name, context, request=request)
        return Fragment(html)

    def standalone_page_title(self, request, fragment, **kwargs):
        """
        Returns the standalone page title.
        """
        return _('Edit Announcement')

    def post(self, request, **kwargs):
        """
        Update Announcement from POST data
        """
        announcement, _ = Announcement.objects.get_or_create(pk=kwargs.get('pk'))
        announcement.content = request.POST.get('content', "")
        announcement.active = request.POST.get('active', False)
        announcement.save()
        return HttpResponseRedirect(reverse('announcements:announcements_list'))


class AnnouncementDeleteView(EdxFragmentView, DeleteView):
    """
    View to delete an announcement
    """
    model = Announcement
    template_name = "announcements/announcement_delete.html"
    success_url = reverse_lazy('announcements:announcements_list')

    def __init__(self, *args, **kwargs):
        super(AnnouncementDeleteView, self).__init__(*args, **kwargs)
        self.object = None

    def render_to_fragment(self, request, **kwargs):
        """
        Render delete confirmation page
        """
        self.object = self.get_object()
        html = render_to_string(self.template_name, self.get_context_data(), request=request)
        return Fragment(html)


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
