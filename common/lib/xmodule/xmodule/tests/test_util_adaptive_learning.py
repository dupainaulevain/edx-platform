"""
Tests for adaptive learning utilities.
"""

import json
import unittest

import httpretty
from mock import DEFAULT, MagicMock, Mock, patch, call

from ..util.adaptive_learning import AdaptiveLearningConfiguration, AdaptiveLearningAPIMixin


ADAPTIVE_LEARNING_CONFIGURATION = {
    'url': 'https://dummy.com',
    'api_version': 'v42',
    'instance_id': 23,
    'access_token': 'this-is-not-a-test',
}

URLS = {
    '_adaptive_learning_url': 'https://dummy.com/v42',
    '_instance_url': 'https://dummy.com/v42/instances/23',
    '_students_url': 'https://dummy.com/v42/instances/23/students',
    '_events_url': 'https://dummy.com/v42/instances/23/events',
    '_knowledge_node_students_url': 'https://dummy.com/v42/instances/23/knowledge_node_students',
    '_pending_reviews_url': 'https://dummy.com/v42/instances/23/review_utils/fetch_reviews'
}

class TestAdaptiveLearningConfiguration(unittest.TestCase):
    """
    Tests for class that stores configuration for interacting with external services
    that provide adaptive learning features.
    """

    def setUp(self):
        self.attributes = {
            'foo': None,
            'bar': 42,
            'baz': 'This is not a test.',
        }
        self.adaptive_learning_configuration = AdaptiveLearningConfiguration(**self.attributes)

    def test_init(self):
        """
        Test that constructor correctly sets attributes.
        """
        self.assertEqual(self.adaptive_learning_configuration._configuration, self.attributes)
        for attribute, value in self.attributes.items():
            self.assertTrue(hasattr(self.adaptive_learning_configuration, attribute))
            self.assertEqual(getattr(self.adaptive_learning_configuration, attribute), value)

    def test_str(self):
        """
        Test string representation of AdaptiveLearningConfiguration object.
        """
        self.assertEqual(
            str(self.adaptive_learning_configuration),
            str(self.adaptive_learning_configuration._configuration)
        )


class DummyModule(AdaptiveLearningAPIMixin):
    """
    Helper class for testing functionality provided by AdaptiveLearningAPIMixin.
    """

    def __init__(self):
        self.course_id = Mock()
        self.course_id.to_deprecated_string.return_value = 'abc'
        self.parent_course = MagicMock()
        self.parent_course.adaptive_learning_configuration = ADAPTIVE_LEARNING_CONFIGURATION


class AdaptiveLearningServiceMixin(object):
    """
    Mixin that provides utility methods for mocking an external adaptive learning service.
    """
    def _mock_request(self, method, url, status, body):
        """
        Register a mock response with HTTP status `status` and response body `body`
        for a request to `url` that uses `method`.
        """
        httpretty.register_uri(method, url, status=status, body=json.dumps(body))

    def _mock_get_request(self, url, body, status=200):
        """
        Register a mock response for a GET request.
        """
        self._mock_request(httpretty.GET, url, status, body)

    def _mock_post_request(self, url, body, status=200):
        """
        Register a mock response for a POST request.
        """
        self._mock_request(httpretty.POST, url, status, body)

    def register_students(self, students):
        """
        Register a mock response listing students that external service knows about.
        """
        self._mock_get_request(URLS['_students_url'], students)

    def register_knowledge_node_students(self, knowledge_node_students):
        """
        Register a mock response listing students that external service knows about.
        """
        self._mock_get_request(URLS['_knowledge_node_students_url'], knowledge_node_students)

    def register_pending_reviews(self, pending_reviews):
        """
        Register a mock response listing students that external service knows about.
        """
        self._mock_get_request(URLS['_pending_reviews_url'], pending_reviews)


@httpretty.activate
class TestAdaptiveLearningAPIMixin(unittest.TestCase, AdaptiveLearningServiceMixin):
    """
    Tests for mixin that provides methods for interacting with external adaptive learning service.

    Note that example data only lists properties of corresponding entities (students, events, etc.)
    that are relevant in the context of individual tests. The external service that provides
    adaptive learning features may return additional properties for different types of entities.
    """

    STUDENTS = [
        {
            'id': n,
            'uid': 'student-{n}'.format(n=n)
        } for n in range(5)
    ]

    KNOWLEDGE_NODE_STUDENTS = [
        {
            'id': n,
            'knowledge_node_id': n,
            'knowledge_node_uid': 'knowledge-node-{n}'.format(n=n),
            'student_id': n,
            'student_uid': 'student-{n}'.format(n=n)
        } for n in range(5)
    ]

    PENDING_REVIEWS = [
        {
            'id': n,
            'student_uid': 'student-{n}'.format(n=n)
        } for n in range(5)
    ]

    def setUp(self):
        self.dummy_module = DummyModule()

    def test__adaptive_learning_configuration(self):
        """
        Test `_adaptive_learning_configuration` property.
        """
        adaptive_learning_configuration = self.dummy_module._adaptive_learning_configuration
        self.assertIsInstance(adaptive_learning_configuration, AdaptiveLearningConfiguration)
        for attribute, value in ADAPTIVE_LEARNING_CONFIGURATION.items():
            self.assertTrue(hasattr(adaptive_learning_configuration, attribute))
            self.assertEqual(getattr(adaptive_learning_configuration, attribute), value)

    def test_urls(self):
        """
        Test that `*_url` properties return appropriate values.
        """
        for url_property, expected_value in URLS.items():
            self.assertTrue(hasattr(self.dummy_module, url_property))
            self.assertEqual(getattr(self.dummy_module, url_property), expected_value)

    def test__request_headers(self):
        """
        Test that `_request_headers` property returns appropriate value.
        """
        expected_headers = {
            'Authorization': 'Token token=this-is-not-a-test'
        }
        self.assertEqual(self.dummy_module._request_headers, expected_headers)

    def test_make_anonymous_user_id(self):
        """
        Test that `make_anonymous_user_id` returns the same ID when called multiple times.
        """
        user_id = 23
        expected_anonymous_user_id = self.dummy_module.make_anonymous_user_id(user_id)
        for dummy in range(5):
            anonymous_user_id = self.dummy_module.make_anonymous_user_id(user_id)
            self.assertEqual(anonymous_user_id, expected_anonymous_user_id)

    def test__get_students(self):
        """
        Test that `_get_students` method returns list of all users that external service knows about.
        """
        self.register_students(self.STUDENTS)
        students = self.dummy_module._get_students()
        self.assertEqual(students, self.STUDENTS)

    def test__get_knowledge_node_students(self):
        """
        Test that `_get_students` method returns list of all users that external service knows about.
        """
        self.register_knowledge_node_students(self.KNOWLEDGE_NODE_STUDENTS)
        knowledge_node_students = self.dummy_module._get_knowledge_node_students()
        self.assertEqual(knowledge_node_students, self.KNOWLEDGE_NODE_STUDENTS)

    def test__get_student(self):
        """
        Test that `_get_student` method returns appropriate information
        if external service knows about a given student,
        and `None` otherwise.
        """
        self.register_students(self.STUDENTS)

        # Unknown student
        student = self.dummy_module._get_student('student-999')
        self.assertIsNone(student)

        # Known students
        for expected_student in self.STUDENTS:
            student = self.dummy_module._get_student(expected_student['uid'])
            self.assertDictEqual(student, expected_student)

    def test__get_knowledge_node_student(self):
        """
        Test that `_get_knowledge_node_student` method returns appropriate information
        if 'knowledge node student' object exists on external service,
        and `None` otherwise.
        """
        self.register_knowledge_node_students(self.KNOWLEDGE_NODE_STUDENTS)

        # Unknown 'knowledge node student' object
        knowledge_node_student = self.dummy_module._get_knowledge_node_student('knowledge-node-999', 'student-999')
        self.assertIsNone(knowledge_node_student)

        # Known 'knowledge node student' object
        for expected_knowledge_node_student in self.KNOWLEDGE_NODE_STUDENTS:
            knowledge_node_student = self.dummy_module._get_knowledge_node_student(
                expected_knowledge_node_student['knowledge_node_uid'],
                expected_knowledge_node_student['student_uid']
            )
            self.assertDictEqual(knowledge_node_student, expected_knowledge_node_student)

    def test_get_pending_reviews(self):
        """
        Test that `_get_student` method returns appropriate information
        if external service knows about a given student,
        and `None` otherwise.
        """
        self.register_pending_reviews(self.PENDING_REVIEWS)

        user_id = 'student-0'
        expected_pending_reviews = self.PENDING_REVIEWS[:1]
        response = Mock()
        response.content = json.dumps(expected_pending_reviews)
        with patch('xmodule.util.adaptive_learning.requests') as patched_requests:
            patched_requests.get.return_value = response
            pending_reviews = self.dummy_module.get_pending_reviews(user_id)
            self.assertEqual(pending_reviews, expected_pending_reviews)
            patched_requests.get.assert_called_once_with(
                self.dummy_module._pending_reviews_url,
                headers=self.dummy_module._request_headers,
                data={'student_uid': user_id}
            )

    def test__create_student(self):
        """
        Test that `_create_student` method creates student on external service, and returns it.
        """
        user_id = 'student-42'
        expected_student = {
            'id': 42,
            'uid': user_id,
        }
        response = Mock()
        response.content = json.dumps(expected_student)
        with patch('xmodule.util.adaptive_learning.requests') as patched_requests:
            patched_requests.post.return_value = response
            student = self.dummy_module._create_student(user_id)
            self.assertDictEqual(student, expected_student)
            patched_requests.post.assert_called_once_with(
                self.dummy_module._students_url,
                headers=self.dummy_module._request_headers,
                data={'uid': user_id}
            )

    def test__create_knowledge_node_student(self):
        """
        Test that `_create_knowledge_node_student` method creates 'knowledge node student' object
        on external service, and returns it.
        """
        block_id = 'knowledge-node-42'
        user_id = 'student-42'
        expected_knowledge_node_student = {
            'id': 23,
            'knowledge_node_id': 23,
            'knowledge_node_uid': block_id,
            'student_id': 23,
            'student_uid': user_id,
        }
        response = Mock()
        response.content = json.dumps(expected_knowledge_node_student)
        with patch('xmodule.util.adaptive_learning.requests') as patched_requests:
            patched_requests.post.return_value = response
            knowledge_node_student = self.dummy_module._create_knowledge_node_student(block_id, user_id)
            self.assertDictEqual(knowledge_node_student, expected_knowledge_node_student)
            patched_requests.post.assert_called_once_with(
                self.dummy_module._knowledge_node_students_url,
                headers=self.dummy_module._request_headers,
                data={'knowledge_node_uid': block_id, 'student_uid': user_id}
            )

    def test_create_knowledge_node_students(self):
        """
        Test that `create_knowledge_node_students` method creates 'knowledge node student' objects
        on external service, and returns them.
        """
        block_ids = [knowledge_node_student['id'] for knowledge_node_student in self.KNOWLEDGE_NODE_STUDENTS]
        user_id = 'student-42'
        with patch.object(
                self.dummy_module, '_get_or_create_knowledge_node_student'
        ) as patched_get_or_create_knowledge_node_student:
            patched_get_or_create_knowledge_node_student.side_effect = self.KNOWLEDGE_NODE_STUDENTS
            knowledge_node_students = self.dummy_module.create_knowledge_node_students(block_ids, user_id)
            self.assertEqual(knowledge_node_students, self.KNOWLEDGE_NODE_STUDENTS)
            patched_get_or_create_knowledge_node_student.assert_has_calls(
                [call(block_id, user_id) for block_id in block_ids]
            )

    def test__create_event(self):
        """
        Test that `_create_event` method creates event of appropriate type on external service,
        and returns it.
        """
        block_id = 'knowledge-node-42'
        user_id = 'student-42'
        event_type = 'DummyEventType'
        expected_event = {
            'id': 42,
            'knowledge_node_student_id': 42,
            'type': 'DummyEventType',
            'payload': None,
        }
        response = Mock()
        response.content = json.dumps(expected_event)
        with patch.object(self.dummy_module, '_get_knowledge_node_student_id') as patched__get_knowledge_node_student_id, \
             patch('xmodule.util.adaptive_learning.requests') as patched_requests:
            patched__get_knowledge_node_student_id.return_value = 23
            patched_requests.post.return_value = response
            event = self.dummy_module._create_event(block_id, user_id, event_type)
            self.assertDictEqual(event, expected_event)
            patched__get_knowledge_node_student_id.assert_called_once_with(block_id, user_id)
            patched_requests.post.assert_called_once_with(
                self.dummy_module._events_url,
                headers=self.dummy_module._request_headers,
                data={'knowledge_node_student_id': 23, 'event_type': event_type}
            )

    def test_create_read_event(self):
        """
        Test that `create_read_event` method creates an event of type `EventRead` on external service,
        and returns it.
        """
        block_id = 'knowledge-node-42'
        user_id = 'student-42'
        expected_event = {
            'id': 42,
            'knowledge_node_student_id': 42,
            'type': 'EventRead',
            'payload': None,
        }
        with patch.object(self.dummy_module, '_create_event') as patched__create_event:
            patched__create_event.return_value = expected_event
            event = self.dummy_module.create_read_event(block_id, user_id)
            self.assertDictEqual(event, expected_event)
            patched__create_event.assert_called_once_with(block_id, user_id, 'EventRead')

    def test__get_or_create_student(self):
        """
        Test that `_get_or_create_student` method creates student on external service if it doesn't exist,
        and returns it.
        """
        self.register_students(self.STUDENTS)

        user_id = 'student-42'
        expected_student = {
            'id': 42,
            'uid': user_id,
        }

        # Student does not exist
        with patch.object(self.dummy_module, '_get_student') as patched__get_student, \
             patch.object(self.dummy_module, '_create_student') as patched__create_student:
            patched__get_student.return_value = None
            patched__create_student.return_value = expected_student
            student = self.dummy_module._get_or_create_student(user_id)
            self.assertDictEqual(student, expected_student)
            patched__get_student.assert_called_once_with(user_id)
            patched__create_student.assert_called_once_with(user_id)

        # Student exists
        with patch.object(self.dummy_module, '_get_student') as patched__get_student, \
             patch.object(self.dummy_module, '_create_student') as patched__create_student:
            patched__get_student.return_value = expected_student
            patched__create_student.return_value = expected_student
            student = self.dummy_module._get_or_create_student(user_id)
            self.assertDictEqual(student, expected_student)
            patched__get_student.assert_called_once_with(user_id)
            patched__create_student.assert_not_called()

    def test_get_or_create_knowledge_node_student(self):
        """
        Test that `_get_or_create_knowledge_node_student` method creates 'knowledge node student' object
        on external service if it doesn't exist, and returns it.
        """
        self.register_students(self.STUDENTS)
        self.register_knowledge_node_students(self.KNOWLEDGE_NODE_STUDENTS)

        student = self.STUDENTS[0]
        block_id = 'knowledge-node-42'
        user_id = student['uid']
        expected_knowledge_node_student = {
            'id': 23,
            'knowledge_node_id': 23,
            'knowledge_node_uid': block_id,
            'student_id': 23,
            'student_uid': user_id,
        }
        # Student does not exist
        with patch.multiple(
                self.dummy_module,
                _get_or_create_student=DEFAULT,
                _get_knowledge_node_student=DEFAULT,
                _create_knowledge_node_student=DEFAULT
        ) as patched_methods:
            patched_methods['_get_or_create_student'].return_value = student
            patched_methods['_get_knowledge_node_student'].return_value = None
            patched_methods['_create_knowledge_node_student'].return_value = expected_knowledge_node_student
            knowledge_node_student = self.dummy_module._get_or_create_knowledge_node_student(block_id, user_id)
            self.assertDictEqual(knowledge_node_student, expected_knowledge_node_student)
            patched_methods['_get_or_create_student'].assert_called_once_with(user_id)
            patched_methods['_get_knowledge_node_student'].assert_called_once_with(block_id, user_id)
            patched_methods['_create_knowledge_node_student'].assert_called_once_with(block_id, user_id)

        # Student exists
        with patch.multiple(
                self.dummy_module,
                _get_or_create_student=DEFAULT,
                _get_knowledge_node_student=DEFAULT,
                _create_knowledge_node_student=DEFAULT
        ) as patched_methods:
            patched_methods['_get_or_create_student'].return_value = student
            patched_methods['_get_knowledge_node_student'].return_value = expected_knowledge_node_student
            patched_methods['_create_knowledge_node_student'].return_value = expected_knowledge_node_student
            student = self.dummy_module._get_or_create_knowledge_node_student(block_id, user_id)
            self.assertDictEqual(student, expected_knowledge_node_student)
            patched_methods['_get_or_create_student'].assert_called_once_with(user_id)
            patched_methods['_get_knowledge_node_student'].assert_called_once_with(block_id, user_id)
            patched_methods['_create_knowledge_node_student'].assert_not_called()

    def test__get_knowledge_node_student_id(self):
        """
        Test the `_get_knowledge_node_student_id` returns ID of a given 'knowledge node student' object.
        """
        block_id = 'knowledge-node-23'
        user_id = 'student-23'
        knowledge_node_student = {
            'id': 42,
            'knowledge_node_id': 23,
            'knowledge_node_uid': block_id,
            'student_id': 23,
            'student_uid': user_id
        }
        with patch.object(self.dummy_module, '_get_or_create_knowledge_node_student') as patched_get_or_create_knowledge_node_student:
            patched_get_or_create_knowledge_node_student.return_value = knowledge_node_student
            knowledge_node_student_id = self.dummy_module._get_knowledge_node_student_id(block_id, user_id)
            self.assertEqual(knowledge_node_student_id, 42)
            patched_get_or_create_knowledge_node_student.assert_called_once_with(block_id, user_id)
