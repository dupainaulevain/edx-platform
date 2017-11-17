"""
Defines URLs for announcements.
"""

from django.conf.urls import url
from util.views import require_global_staff

from .views import AnnouncementsView, AnnouncementEditView, AnnouncementDeleteView

urlpatterns = [
    url(
        r'^(?P<page>\d+)?$',
        require_global_staff(AnnouncementsView.as_view()),
        name='openedx.announcements.announcements_list',
    ),
    url(
        r'^create$',
        require_global_staff(AnnouncementEditView.as_view()),
        name='openedx.announcements.announcements_create',
    ),
    url(
        r'^edit/(?P<pk>\d+)?$',
        require_global_staff(AnnouncementEditView.as_view()),
        name='openedx.announcements.announcements_edit',
    ),
    url(
        r'^delete/(?P<pk>\d+)?$',
        require_global_staff(AnnouncementDeleteView.as_view()),
        name='openedx.announcements.announcements_delete',
    ),
]
