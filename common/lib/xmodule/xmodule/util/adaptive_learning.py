# -*- coding: utf-8 -*-
"""
Utilities for adaptive learning features.
"""

import hashlib
import json
import logging
import requests

from lazy import lazy

log = logging.getLogger(__name__)


class AdaptiveLearningConfiguration(object):
    """
    Stores configuration that is necessary for interacting with external services
    that provide adaptive learning features.
    """

    def __init__(self, **kwargs):
        """
        Creates an attribute for each key in `kwargs` and sets it to the corresponding value.
        """
        self._configuration = kwargs
        for attr, value in kwargs.items():
            setattr(self, attr, value)

    def __str__(self):
        """
        Returns string listing all custom attributes set on `self`.
        """
        return str(self._configuration)


class AdaptiveLearningAPIMixin(object):
    """
    Provides methods for interacting with external service that provides adaptive learning features.
    """

    @lazy
    def _adaptive_learning_configuration(self):
        """
        Return configuration for accessing external service that provides adaptive learning features.

        This configuration is a course-wide setting, so in order to access it,
        we need to (lazily) load the parent course from the DB.
        """
        course = self.parent_course
        return AdaptiveLearningConfiguration(
            **course.adaptive_learning_configuration
        )

    @lazy
    def _adaptive_learning_url(self):
        """
        Return base URL for external service that provides adaptive learning features.

        The base URL is a combination of the URL (url) and API version (api_version)
        specified in the adaptive learning configuration for the parent course.
        """
        url = self._adaptive_learning_configuration.url
        api_version = self._adaptive_learning_configuration.api_version
        return '{url}/{api_version}'.format(url=url, api_version=api_version)

    @lazy
    def _instance_url(self):
        """
        Return URL for requesting instance-specific data from external service
        that provides adaptive learning features.
        """
        instance_id = self._adaptive_learning_configuration.instance_id
        return '{base_url}/instances/{instance_id}'.format(
            base_url=self._adaptive_learning_url, instance_id=instance_id
        )

    @lazy
    def _students_url(self):
        """
        Return URL for requests dealing with students.
        """
        return '{base_url}/students'.format(base_url=self._instance_url)

    @lazy
    def _events_url(self):
        """
        Return URL for requests dealing with events.
        """
        return '{base_url}/events'.format(base_url=self._instance_url)

    @lazy
    def _knowledge_node_students_url(self):
        """
        Return URL for accessing 'knowledge node student' objects.
        """
        return '{base_url}/knowledge_node_students'.format(base_url=self._instance_url)

    @lazy
    def _pending_reviews_url(self):
        """
        Return URL for accessing pending reviews.
        """
        return '{base_url}/review_utils/fetch_reviews'.format(base_url=self._instance_url)

    @lazy
    def _request_headers(self):
        """
        Return custom headers for requests to external service that provides adaptive learning features.
        """
        access_token = self._adaptive_learning_configuration.access_token
        return {
            'Authorization': 'Token token={access_token}'.format(access_token=access_token)
        }

    def _get_knowledge_node_student_id(self, block_id, user_id):
        """
        Return ID of 'knowledge node student' object linking student identified by `user_id`
        to unit identified by `block_id`.
        """
        knowledge_node_student = self._get_or_create_knowledge_node_student(block_id, user_id)
        return knowledge_node_student.get('id')

    def _get_or_create_knowledge_node_student(self, block_id, user_id):
        """
        Return 'knowledge node student' object for user identified by `user_id`
        and unit identified by `block_id`.
        """
        # Create student
        self._get_or_create_student(user_id)
        # Link student to unit
        knowledge_node_student = self._get_knowledge_node_student(block_id, user_id)
        if knowledge_node_student is None:
            knowledge_node_student = self._create_knowledge_node_student(block_id, user_id)
        return knowledge_node_student

    def _get_or_create_student(self, user_id):
        """
        Create a new student on external service if it doesn't exist,
        and return it.
        """
        student = self._get_student(user_id)
        if student is None:
            student = self._create_student(user_id)
        return student

    def _get_student(self, user_id):
        """
        Return external information about student identified by `user_id`,
        or None if external service does not know about student.
        """
        students = self._get_students()
        try:
            student = next(s for s in students if s.get('uid') == user_id)
        except StopIteration:
            student = None
        return student

    def _get_students(self):
        """
        Return list of all students that external service knows about.
        """
        url = self._students_url
        response = requests.get(url, headers=self._request_headers)
        students = json.loads(response.content)
        return students

    def _create_student(self, user_id):
        """
        Create student identified by `user_id` on external service,
        and return it.
        """
        url = self._students_url
        payload = {'uid': user_id}
        response = requests.post(url, headers=self._request_headers, data=payload)
        student = json.loads(response.content)
        return student

    def _get_knowledge_node_student(self, block_id, user_id):
        """
        Return 'knowledge node student' object for user identified by `user_id`
        and unit identified by `block_id`, or None if it does not exist.
        """
        # Get 'knowledge node student' objects
        links = self._get_knowledge_node_students()
        # Filter them by `block_id` and `user_id`
        try:
            link = next(
                l for l in links if l.get('knowledge_node_uid') == block_id and l.get('student_uid') == user_id
            )
        except StopIteration:
            link = None
        return link

    def _get_knowledge_node_students(self):
        """
        Return list of all 'knowledge node student' objects for this course.
        """
        url = self._knowledge_node_students_url
        response = requests.get(url, headers=self._request_headers)
        links = json.loads(response.content)
        return links

    def _create_knowledge_node_student(self, block_id, user_id):
        """
        Create 'knowledge node student' object that links student identified by `user_id`
        to unit identified by `block_id`, and return it.
        """
        url = self._knowledge_node_students_url
        payload = {'knowledge_node_uid': block_id, 'student_uid': user_id}
        response = requests.post(url, headers=self._request_headers, data=payload)
        knowledge_node_student = json.loads(response.content)
        return knowledge_node_student

    def _create_event(self, block_id, user_id, event_type):
        """
        Create event of type `event_type` for unit identified by `block_id` and student identified by `user_id`.
        """
        url = self._events_url
        knowledge_node_student_id = self._get_knowledge_node_student_id(block_id, user_id)
        payload = {
            'knowledge_node_student_id': knowledge_node_student_id,
            'event_type': event_type,
        }
        # Send request
        response = requests.post(url, headers=self._request_headers, data=payload)
        event = json.loads(response.content)
        return event

    # Public API

    def make_anonymous_user_id(self, user_id):
        """
        Return anonymous ID for user identified by `user_id`.

        Incorporate `course_id` and access token for external service into digest.
        """
        # Include the access token for this course as a salt
        hasher = hashlib.md5()
        hasher.update(self._adaptive_learning_configuration.access_token)
        hasher.update(unicode(user_id))
        hasher.update(self.course_id.to_deprecated_string().encode('utf-8'))
        anonymous_user_id = hasher.hexdigest()
        return anonymous_user_id

    def create_read_event(self, block_id, user_id):
        """
        Create read event for unit identified by `block_id` and student identified by `user_id`.
        """
        return self._create_event(block_id, user_id, 'EventRead')

    def create_knowledge_node_students(self, block_ids, user_id):
        """
        Create 'knowledge node student' objects that link student identified by `user_id`
        to review questions identified by block IDs listed in `block_ids`, and return them.
        """
        knowledge_node_students = []
        for block_id in block_ids:
            knowledge_node_student = self._get_or_create_knowledge_node_student(block_id, user_id)
            knowledge_node_students.append(knowledge_node_student)
        return knowledge_node_students

    def get_pending_reviews(self, user_id):
        """
        Return pending reviews for user identified by `user_id`.
        """
        url = self._pending_reviews_url
        payload = {'student_uid': user_id}
        response = requests.get(url, headers=self._request_headers, data=payload)
        pending_reviews_user = json.loads(response.content)
        return pending_reviews_user
