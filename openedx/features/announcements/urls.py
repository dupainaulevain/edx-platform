"""
Defines URLs for announcements.
"""

from django.conf.urls import patterns, url
from util.views import require_global_staff

from .views import AnnouncementsView, AnnouncementEditView, AnnouncementDeleteView

urlpatterns = patterns(
    'openedx.features.announcements.views',
    url(
        r'^(?P<page>\d+)?$',
        require_global_staff(AnnouncementsView.as_view()),
        name='announcements_list',
    ),
    url(
        r'^create$',
        require_global_staff(AnnouncementEditView.as_view()),
        name='announcements_create',
    ),
    url(
        r'^edit/(?P<pk>\d+)?$',
        require_global_staff(AnnouncementEditView.as_view()),
        name='announcements_edit',
    ),
    url(
        r'^delete/(?P<pk>\d+)?$',
        require_global_staff(AnnouncementDeleteView.as_view()),
        name='announcements_delete',
    ),
)
