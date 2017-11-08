"""
Defines URLs for announcements in the LMS.
"""

from django.conf.urls import patterns, url
from django.contrib.auth.decorators import login_required

from .views import AnnouncementsJSONView

urlpatterns = patterns(
    'openedx.features.announcements.lms_views',
    url(
        r'^page/(?P<page>\d+)$',
        login_required(AnnouncementsJSONView.as_view()),
        name='announcements_page',
    ),
)
