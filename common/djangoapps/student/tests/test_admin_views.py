"""
Tests student admin.py
"""
import datetime
import ddt
from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.conf import settings
from django.forms import ValidationError
from django.urls import reverse
from django.test import TestCase, overide_settings
from mock import Mock

from student.admin import COURSE_ENROLLMENT_ADMIN_SWITCH, UserAdmin
from student.models import LoginFailures
from student.tests.factories import CourseEnrollmentFactory, UserFactory
from xmodule.modulestore.tests.django_utils import SharedModuleStoreTestCase
from xmodule.modulestore.tests.factories import CourseFactory


class AdminCourseRolesPageTest(SharedModuleStoreTestCase):
    """Test the django admin course roles form saving data in db.
    """
    @classmethod
    def setUpClass(cls):
        super(AdminCourseRolesPageTest, cls).setUpClass()
        cls.course = CourseFactory.create(org='edx')

    def setUp(self):
        super(AdminCourseRolesPageTest, self).setUp()
        self.user = UserFactory.create(is_staff=True, is_superuser=True)
        self.user.save()

    def test_save_valid_data(self):

        data = {
            'course_id': unicode(self.course.id),
            'role': 'finance_admin',
            'org': 'edx',
            'email': self.user.email
        }

        self.client.login(username=self.user.username, password='test')

        # # adding new role from django admin page
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertRedirects(response, reverse('admin:student_courseaccessrole_changelist'))

        response = self.client.get(reverse('admin:student_courseaccessrole_changelist'))
        self.assertContains(response, 'Select course access role to change')
        self.assertContains(response, 'Add course access role')
        self.assertContains(response, 'finance_admin')
        self.assertContains(response, unicode(self.course.id))
        self.assertContains(response, '1 course access role')

        #try adding with same information raise error.
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertContains(response, 'Duplicate')

    def test_save_without_org_and_course_data(self):

        data = {
            'role': 'staff',
            'email': self.user.email,
            'course_id': unicode(self.course.id)
        }

        self.client.login(username=self.user.username, password='test')

        # # adding new role from django admin page
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertRedirects(response, reverse('admin:student_courseaccessrole_changelist'))

        response = self.client.get(reverse('admin:student_courseaccessrole_changelist'))
        self.assertContains(response, 'staff')
        self.assertContains(response, '1 course access role')

    def test_save_with_course_only(self):

        data = {
            'role': 'beta_testers',
            'email': self.user.email,

        }

        self.client.login(username=self.user.username, password='test')

        # # adding new role from django admin page
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertRedirects(response, reverse('admin:student_courseaccessrole_changelist'))

        response = self.client.get(reverse('admin:student_courseaccessrole_changelist'))
        self.assertContains(response, 'beta_testers')
        self.assertContains(response, '1 course access role')

    def test_save_with_org_only(self):

        data = {
            'role': 'beta_testers',
            'email': self.user.email,
            'org': 'myorg'

        }

        self.client.login(username=self.user.username, password='test')

        # # adding new role from django admin page
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertRedirects(response, reverse('admin:student_courseaccessrole_changelist'))

        response = self.client.get(reverse('admin:student_courseaccessrole_changelist'))
        self.assertContains(response, 'myorg')
        self.assertContains(response, '1 course access role')

    def test_save_with_invalid_course(self):

        course = unicode('no/edx/course')
        email = "invalid@email.com"
        data = {
            'course_id': course,
            'role': 'finance_admin',
            'org': 'edx',
            'email': email
        }

        self.client.login(username=self.user.username, password='test')

        # Adding new role with invalid data
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertContains(
            response,
            'Course not found. Entered course id was: &quot;{}&quot;.'.format(
                course
            )
        )

        self.assertContains(
            response,
            "Email does not exist. Could not find {}. Please re-enter email address".format(
                email
            )
        )

    def test_save_valid_course_invalid_org(self):

        data = {
            'course_id': unicode(self.course.id),
            'role': 'finance_admin',
            'org': 'edxxx',
            'email': self.user.email
        }

        self.client.login(username=self.user.username, password='test')

        # # adding new role from django admin page
        response = self.client.post(reverse('admin:student_courseaccessrole_add'), data=data)
        self.assertContains(
            response,
            'Org name {} is not valid. Valid name is {}.'.format(
                'edxxx', 'edx'
            )
        )


class AdminUserPageTest(TestCase):
    """
    Unit tests for the UserAdmin view.
    """
    def setUp(self):
        super(AdminUserPageTest, self).setUp()
        self.admin = UserAdmin(User, AdminSite())

    def test_username_is_writable_for_user_creation(self):
        """
        Ensures that the username is not readonly, when admin creates new user.
        """
        request = Mock()
        self.assertNotIn('username', self.admin.get_readonly_fields(request))

    def test_username_is_readonly_for_user(self):
        """
        Ensures that the username field is readonly, when admin open user which already exists.

        This hook used for skip Django validation in the `auth_user_change` view.

        Changing the username is still possible using the database or from the model directly.

        However, changing the username might cause issues with the logs and/or the cs_comments_service since it
        stores the username in a different database.
        """
        request = Mock()
        user = Mock()
        self.assertIn('username', self.admin.get_readonly_fields(request, user))


@ddt.ddt
class CourseEnrollmentAdminTest(SharedModuleStoreTestCase):
    """
    Unit tests for the CourseEnrollmentAdmin view.
    """
    ADMIN_URLS = (
        ('get', reverse('admin:student_courseenrollment_add')),
        ('get', reverse('admin:student_courseenrollment_changelist')),
        ('get', reverse('admin:student_courseenrollment_change', args=(1,))),
        ('get', reverse('admin:student_courseenrollment_delete', args=(1,))),
        ('post', reverse('admin:student_courseenrollment_add')),
        ('post', reverse('admin:student_courseenrollment_changelist')),
        ('post', reverse('admin:student_courseenrollment_change', args=(1,))),
        ('post', reverse('admin:student_courseenrollment_delete', args=(1,))),
    )

    def setUp(self):
        super(CourseEnrollmentAdminTest, self).setUp()
        self.user = UserFactory.create(is_staff=True, is_superuser=True)
        self.course = CourseFactory()
        self.course_enrollment = CourseEnrollmentFactory(
            user=self.user,
            course_id=self.course.id,  # pylint: disable=no-member
        )
        self.client.login(username=self.user.username, password='test')

    @ddt.data(*ADMIN_URLS)
    @ddt.unpack
    def test_view_disabled(self, method, url):
        """
        All CourseEnrollmentAdmin views are disabled by default.
        """
        response = getattr(self.client, method)(url)
        self.assertEqual(response.status_code, 403)

    @ddt.data(*ADMIN_URLS)
    @ddt.unpack
    def test_view_enabled(self, method, url):
        """
        Ensure CourseEnrollmentAdmin views can be enabled with the waffle switch.
        """
        with COURSE_ENROLLMENT_ADMIN_SWITCH.override(active=True):
            response = getattr(self.client, method)(url)
        self.assertEqual(response.status_code, 200)

    def test_username_exact_match(self):
        """
        Ensure that course enrollment searches return exact matches on username first.
        """
        user2 = UserFactory.create(username='aaa_{}'.format(self.user.username))
        CourseEnrollmentFactory(
            user=user2,
            course_id=self.course.id,  # pylint: disable=no-member
        )
        search_url = '{}?q={}'.format(reverse('admin:student_courseenrollment_changelist'), self.user.username)
        with COURSE_ENROLLMENT_ADMIN_SWITCH.override(active=True):
            response = self.client.get(search_url)
        self.assertEqual(response.status_code, 200)

        # context['results'] is an array of arrays of HTML <td> elements to be rendered
        self.assertEqual(len(response.context['results']), 2)
        for idx, username in enumerate([self.user.username, user2.username]):
            # Locate the <td> column containing the username
            user_field = next(col for col in response.context['results'][idx] if "field-user" in col)
            self.assertIn(username, user_field)

    def test_save_toggle_active(self):
        """
        Edit a CourseEnrollment to toggle its is_active checkbox, save it and verify that it was toggled.
        When the form is saved, Django uses a QueryDict object which is immutable and needs special treatment.
        This test implicitly verifies that the POST parameters are handled correctly.
        """
        # is_active will change from True to False
        self.assertTrue(self.course_enrollment.is_active)
        data = {
            'user': unicode(self.course_enrollment.user.id),
            'course': unicode(self.course_enrollment.course.id),
            'is_active': 'false',
            'mode': self.course_enrollment.mode,
        }

        with COURSE_ENROLLMENT_ADMIN_SWITCH.override(active=True):
            response = self.client.post(
                reverse('admin:student_courseenrollment_change', args=(self.course_enrollment.id, )),
                data=data,
            )
        self.assertEqual(response.status_code, 302)

        self.course_enrollment.refresh_from_db()
        self.assertFalse(self.course_enrollment.is_active)

    def test_save_invalid_course_id(self):
        """
        Send an invalid course ID instead of "org.0/course_0/Run_0" when saving, and verify that it fails.
        """
        data = {
            'user': unicode(self.course_enrollment.user.id),
            'course': 'invalid-course-id',
            'is_active': 'true',
            'mode': self.course_enrollment.mode,
        }

        with COURSE_ENROLLMENT_ADMIN_SWITCH.override(active=True):
            with self.assertRaises(ValidationError):
                self.client.post(
                    reverse('admin:student_courseenrollment_change', args=(self.course_enrollment.id, )),
                    data=data,
                )


@ddt.ddt
class LoginFailuresAdminTest(TestCase):
    """Test Login Failures Admin."""

    @classmethod
    def setUpClass(cls):
        """Setup Class."""
        super(LoginFailuresAdminTest, self).setUpClass(cls)
        self.user = UserFactory.create(is_staff=True, is_superuser=True)
        self.client.login(username=self.user.username, password='test')

    def setUp(self):
        """Setup."""
        user = UserFactory.create()
        LoginFailures.objects.create(user=self.user, failure_count=10, lockout_until=datetime.datetime.now())
        LoginFailures.objects.create(user=user, failure_count=2)

    def tearDown(self):
        """Tear Down."""
        LoginFailures.objects.all().delete()

    @ddt.data(
        reverse('admin:student_loginfailures_changelist'),
        reverse('admin:student_loginfailures_add'),
        reverse('admin:student_loginfailures_change', args=(1,)),
        reverse('admin:student_loginfailures_delete', args(1,)),
    )
    def test_feature_disabled(self, url):
        """Test if feature is disabled there's no access to the admin module."""
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)

    def test_unlock_student_accounts(self):
        """Test batch unlock student accounts."""
        url = reverse('admin:student_loginfailures_change')
        with override_settings(
            FEATURES=dict(
                settings.FEATURES,
                **{'ENABLE_MAX_FAILED_LOGIN_ATTEMPTS': True}
            )
        ):
            response = self.client.post(
                url,
                {'action': 'unlock_student_accounts',
                 '_selected_action': [unicode(o.pk) for o in LoginFailures.objects.all()]}
            )
        count = LoginFailures.objects.count()
        self.assertEqual(count, 0)

    def test_unlock_account(self):
        """Test unlock single student account."""
        url = reverse('admin:student_loginfailures_change')
        start_count = LoginFailures.objects.count()
        with override_settings(
            FEATURES=dict(
                settings.FEATURES,
                **{'ENABLE_MAX_FAILED_LOGIN_ATTEMPTS': True}
            )
        ):
            response = self.client.post(
                url,
                {'action': 'unlock_student_accounts',
                 '_selected_action': [unicode(o.pk) for o in LoginFailures.objects.first()],
                 '_unlock': {}}
            )
        count = LoginFailures.objects.count()
        self.assertEqual(count, start_count-1)
