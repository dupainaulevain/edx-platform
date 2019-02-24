"""
Unit tests for the announcements feature.
"""

import json
import unittest
from mock import patch

from django.conf import settings
from django.test import TestCase
from django.test.client import Client
from django.core.urlresolvers import reverse

from student.tests.factories import AdminFactory

from openedx.features.announcements.models import Announcement

TEST_ANNOUNCEMENTS = [
    ("Active Announcement", True),
    ("Inactive Announcement", False),
    ("Another Test Announcement", True),
    ("<strong>Formatted Announcement</strong>", True),
    ("<a>Other Formatted Announcement</a>", True),
]


@unittest.skipUnless(settings.ROOT_URLCONF == 'lms.urls', 'Test only valid in lms')
class TestGlobalAnnouncements(TestCase):
    """
    Test Announcements in LMS
    """

    @classmethod
    def setUpTestData(cls):
        Announcement.objects.bulk_create([
            Announcement(content=content, active=active)
            for content, active in TEST_ANNOUNCEMENTS
        ])

    def setUp(self):
        self.client = Client()
        self.admin = AdminFactory.create(
            email='staff@edx.org',
            username='admin',
            password='pass'
        )
        self.client.login(username=self.admin.username, password='pass')

    @patch.dict(settings.FEATURES, {'ENABLE_ANNOUNCEMENTS': False})
    def test_feature_flag_disabled(self):
        """Ensures that the default settings effectively disables the feature"""
        response = self.client.get('/dashboard')
        self.assertNotIn('AnnouncementsView', response.content)
        self.assertNotIn('<div id="announcements"', response.content)

    def test_feature_flag_enabled(self):
        """Ensures that enabling the flag, enables the feature"""
        response = self.client.get('/dashboard')
        self.assertIn('AnnouncementsView', response.content)

    def test_pagination(self):
        url = reverse("announcements_page", kwargs={"page": 1})
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEquals(data['num_pages'], 1)
        ## double the number of announcements to verify the number of pages increases
        self.setUpTestData()
        response = self.client.get(url)
        data = json.loads(response.content)
        self.assertEquals(data['num_pages'], 2)

    def test_active(self):
        """
        Ensures that active announcements are visible on the dashboard
        """
        url = reverse("announcements_page", kwargs={"page": 1})
        response = self.client.get(url)
        self.assertIn("Active Announcement", response.content)

    def test_inactive(self):
        """
        Ensures that inactive announcements aren't visible on the dashboard
        """
        url = reverse("announcements_page", kwargs={"page": 1})
        response = self.client.get(url)
        self.assertNotIn("Inactive Announcement", response.content)

    def test_formatted(self):
        """
        Ensures that formatting in announcements is rendered properly
        """
        url = reverse("announcements_page", kwargs={"page": 1})
        response = self.client.get(url)
        self.assertIn("<strong>Formatted Announcement</strong>", response.content)


@unittest.skipUnless(settings.ROOT_URLCONF == 'cms.urls', 'Test only valid in studio')
class TestGlobalAnnouncementsStudio(TestCase):
    """
    Test Announcements in Studio
    """

    def setUp(self):
        self.client = Client()
        self.admin = AdminFactory.create(
            email='staff@edx.org',
            username='admin',
            password='pass'
        )
        self.client.login(username=self.admin.username, password='pass')

    def test_create(self):
        """
        Test create announcement view
        """
        url = reverse("openedx.announcements.announcements_create")
        self.client.post(url, {"content": "Test Create Announcement", "active": True})
        result = Announcement.objects.filter(content="Test Create Announcement").exists()
        self.assertTrue(result)

    def test_edit(self):
        """
        Test edit announcement view
        """
        announcement = Announcement.objects.create(content="test")
        announcement.save()
        url = reverse("openedx.announcements.announcements_edit", kwargs={"pk": announcement.pk})
        response = self.client.get(url)
        self.assertIn('<div class="wrapper-content wrapper announcements-editor">', response.content)
        self.client.post(url, {"content": "Test Edit Announcement", "active": True})
        announcement = Announcement.objects.get(pk=announcement.pk)
        self.assertEquals(announcement.content, "Test Edit Announcement")

    def test_delete(self):
        """
        Test delete announcement view
        """
        announcement = Announcement.objects.create(content="Test Delete")
        announcement.save()
        url = reverse("openedx.announcements.announcements_delete", kwargs={"pk": announcement.pk})
        self.client.get(url)
        result = Announcement.objects.filter(content="Test Edit Announcement").exists()
        self.assertFalse(result)
