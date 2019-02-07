# -*- coding: utf-8 -*-
"""
CAPA Problems XBlock
"""
import json
import logging
import os
import re
import sys

from fs.osfs import OSFS
from lxml import etree

from django.conf import settings
from django.core.cache import cache as django_cache
from django.contrib.staticfiles.storage import staticfiles_storage
from django.urls import reverse
from requests.auth import HTTPBasicAuth
from six import text_type
from webob import Response
from webob.multidict import MultiDict
from web_fragments.fragment import Fragment
from xblock.core import XBlock
from xblock.fields import Boolean, Dict, Float, Integer, Scope, String, XMLString
from xblock.mixins import IndexInfoMixin
from xblockutils.resources import ResourceLoader
from xblockutils.studio_editable import StudioEditableXBlockMixin

from openedx.core.lib.xblock_builtin import get_css_dependencies, get_js_dependencies
from xmodule.contentstore.django import contentstore
from xmodule.exceptions import NotFoundError, ProcessingError
from xmodule.fields import Date, Timedelta, ScoreField
from xmodule.graders import ShowCorrectness
from xmodule.raw_module import RawDescriptor
from xmodule.util.misc import escape_html_characters
from xmodule.xml_module import XmlParserMixin
from xmodule.x_module import ResourceTemplates
from xmodule.util.sandboxing import get_python_lib_zip, can_execute_unsafe_code

from .capa_base import _, Randomization, CapaMixin, ComplexEncoder
from .capa_base_constants import RANDOMIZATION, SHOWANSWER
from xblock_capa.lib import responsetypes
from xblock_capa.lib.capa_problem import LoncapaProblem, LoncapaSystem
from xblock_capa.lib.xqueue_interface import XQueueInterface


log = logging.getLogger(__name__)
loader = ResourceLoader(__name__)  # pylint: disable=invalid-name
FEATURES = getattr(settings, 'FEATURES', {})


@XBlock.wants('user')
@XBlock.needs('i18n')
@XBlock.needs('request')
class CapaXBlock(XBlock, CapaMixin, ResourceTemplates, XmlParserMixin, IndexInfoMixin, StudioEditableXBlockMixin):
    """
    An XBlock implementing LonCapa format problems, by way of
    xblock_capa.lib.capa_problem.LoncapaProblem
    """
    display_name = String(
        display_name=_("Display Name"),
        help=_("The display name for this component."),
        scope=Scope.settings,
        # it'd be nice to have a useful default but it screws up other things; so,
        # use display_name_with_default for those
        default=_("Blank Advanced Problem")
    )
    attempts = Integer(
        help=_("Number of attempts taken by the student on this problem"),
        default=0,
        scope=Scope.user_state
    )
    max_attempts = Integer(
        display_name=_("Maximum Attempts"),
        help=_("Defines the number of times a student can try to answer this problem. "
               "If the value is not set, infinite attempts are allowed."),
        values={"min": 0}, scope=Scope.settings
    )
    due = Date(help=_("Date that this problem is due by"), scope=Scope.settings)
    graceperiod = Timedelta(
        help=_("Amount of time after the due date that submissions will be accepted"),
        scope=Scope.settings
    )
    show_correctness = String(
        display_name=_("Show Results"),
        help=_("Defines when to show whether a learner's answer to the problem is correct. "
               "Configured on the subsection."),
        scope=Scope.settings,
        default=ShowCorrectness.ALWAYS,
        values=[
            {"display_name": _("Always"), "value": ShowCorrectness.ALWAYS},
            {"display_name": _("Never"), "value": ShowCorrectness.NEVER},
            {"display_name": _("Past Due"), "value": ShowCorrectness.PAST_DUE},
        ],
    )
    showanswer = String(
        display_name=_("Show Answer"),
        help=_("Defines when to show the answer to the problem. "
               "A default value can be set in Advanced Settings."),
        scope=Scope.settings,
        default=SHOWANSWER.FINISHED,
        values=[
            {"display_name": _("Always"), "value": SHOWANSWER.ALWAYS},
            {"display_name": _("Answered"), "value": SHOWANSWER.ANSWERED},
            {"display_name": _("Attempted"), "value": SHOWANSWER.ATTEMPTED},
            {"display_name": _("Closed"), "value": SHOWANSWER.CLOSED},
            {"display_name": _("Finished"), "value": SHOWANSWER.FINISHED},
            {"display_name": _("Correct or Past Due"), "value": SHOWANSWER.CORRECT_OR_PAST_DUE},
            {"display_name": _("Past Due"), "value": SHOWANSWER.PAST_DUE},
            {"display_name": _("Never"), "value": SHOWANSWER.NEVER}]
    )
    force_save_button = Boolean(
        help=_("Whether to force the save button to appear on the page"),
        scope=Scope.settings,
        default=False
    )
    reset_key = "DEFAULT_SHOW_RESET_BUTTON"
    default_reset_button = getattr(settings, reset_key) if hasattr(settings, reset_key) else False
    show_reset_button = Boolean(
        display_name=_("Show Reset Button"),
        help=_("Determines whether a 'Reset' button is shown so the user may reset their answer. "
               "A default value can be set in Advanced Settings."),
        scope=Scope.settings,
        default=default_reset_button
    )
    rerandomize = Randomization(
        display_name=_("Randomization"),
        help=_(
            'Defines when to randomize the variables specified in the associated Python script. '
            'For problems that do not randomize values, specify \"Never\". '
        ),
        default=RANDOMIZATION.NEVER,
        scope=Scope.settings,
        values=[
            {"display_name": _("Always"), "value": RANDOMIZATION.ALWAYS},
            {"display_name": _("On Reset"), "value": RANDOMIZATION.ONRESET},
            {"display_name": _("Never"), "value": RANDOMIZATION.NEVER},
            {"display_name": _("Per Student"), "value": RANDOMIZATION.PER_STUDENT}
        ]
    )
    data = XMLString(
        help=_("XML data for the problem"),
        scope=Scope.content,
        enforce_type=FEATURES.get('ENABLE_XBLOCK_XML_VALIDATION', True),
        default="<problem></problem>"
    )
    correct_map = Dict(help=_("Dictionary with the correctness of current student answers"),
                       scope=Scope.user_state, default={})
    input_state = Dict(help=_("Dictionary for maintaining the state of inputtypes"), scope=Scope.user_state)
    student_answers = Dict(help=_("Dictionary with the current student responses"), scope=Scope.user_state)

    # enforce_type is set to False here because this field is saved as a dict in the database.
    score = ScoreField(help=_("Dictionary with the current student score"), scope=Scope.user_state, enforce_type=False)
    has_saved_answers = Boolean(help=_("Whether or not the answers have been saved since last submit"),
                                scope=Scope.user_state, default=False)
    done = Boolean(help=_("Whether the student has answered the problem"), scope=Scope.user_state, default=False)
    seed = Integer(help=_("Random seed for this student"), scope=Scope.user_state)
    last_submission_time = Date(help=_("Last submission time"), scope=Scope.user_state)
    submission_wait_seconds = Integer(
        display_name=_("Timer Between Attempts"),
        help=_("Seconds a student must wait between submissions for a problem with multiple attempts."),
        scope=Scope.settings,
        default=0)
    weight = Float(
        display_name=_("Problem Weight"),
        help=_("Defines the number of points each problem is worth. "
               "If the value is not set, each response field in the problem is worth one point."),
        values={"min": 0, "step": .1},
        scope=Scope.settings
    )
    markdown = String(help=_("Markdown source of this module"), default=None, scope=Scope.settings)
    source_code = String(
        help=_("Source code for LaTeX and Word problems. This feature is not well-supported."),
        scope=Scope.settings
    )
    use_latex_compiler = Boolean(
        help=_("Enable LaTeX templates?"),
        default=False,
        scope=Scope.settings
    )
    matlab_api_key = String(
        display_name=_("Matlab API key"),
        help=_("Enter the API key provided by MathWorks for accessing the MATLAB Hosted Service. "
               "This key is granted for exclusive use by this course for the specified duration. "
               "Please do not share the API key with other courses and notify MathWorks immediately "
               "if you believe the key is exposed or compromised. To obtain a key for your course, "
               "or to report an issue, please contact moocsupport@mathworks.com"),
        scope=Scope.settings
    )

    INDEX_CONTENT_TYPE = 'CAPA'
    icon_class = 'problem'

    template_dir_name = 'problem'
    template_packages = [__name__]

    editable_fields = [
        "display_name",
        "matlab_api_key",
        "max_attempts",
        "weight",
        "rerandomize",
        "showanswer",
        "show_reset_button",
        "submission_wait_seconds",
    ]

    studio_tabs_fields = [
        'data',
        'markdown',
        "source_code",
        "use_latex_compiler",
    ]

    tabs_templates_dir = os.path.join('templates', 'studio')
    studio_tabs = [
        'editor',
    ]

    # The capa format specifies that what we call max_attempts in the code
    # is the attribute `attempts`. This will do that conversion
    metadata_translations = dict(RawDescriptor.metadata_translations)
    metadata_translations['attempts'] = 'max_attempts'

    def __init__(self, *args, **kwargs):
        """
        Parses the provided XML data to ensure that bad data does not make it into the modulestore.

        Raises lxml.etree.XMLSyntaxError if bad XML is provided.
        """
        super(CapaXBlock, self).__init__(*args, **kwargs)

        etree.XML(self.data)

    # VS[compat]
    # TODO (cpennington): Delete this method once all fall 2012 course are being
    # edited in the cms
    @classmethod
    def backcompat_paths(cls, path):
        return [
            'problems/' + path[8:],
            path[8:],
        ]

    def index_dictionary(self):
        """
        Return dictionary prepared with module content and type for search indexing.
        """
        xblock_body = super(CapaXBlock, self).index_dictionary()
        # Removing solutions and hints, as well as script and style
        capa_content = re.sub(
            re.compile(
                r"""
                    <solution>.*?</solution> |
                    <script>.*?</script> |
                    <style>.*?</style> |
                    <[a-z]*hint.*?>.*?</[a-z]*hint>
                """,
                re.DOTALL |
                re.VERBOSE),
            "",
            self.data
        )
        capa_content = escape_html_characters(capa_content)
        capa_body = {
            "capa_content": capa_content,
            "display_name": self.display_name,
        }
        if "content" in xblock_body:
            xblock_body["content"].update(capa_body)
        else:
            xblock_body["content"] = capa_body
        xblock_body["content_type"] = self.INDEX_CONTENT_TYPE
        xblock_body["problem_types"] = list(self.problem_types)
        return xblock_body

    @classmethod
    def get_template_dir(cls):
        return os.path.join('templates', cls.template_dir_name)

    @classmethod
    def filter_templates(cls, template, course):
        """
        Filter template that contains 'latex' from templates.

        Show them only if use_latex_compiler is set to True in
        course settings.
        """
        return 'latex' not in template['template_id'] or course.use_latex_compiler

    def student_view(self, context=None):  # pylint: disable=unused-argument
        """
        Return a fragment with the HTML/JS/CSS from this XBlock

        When run within the Studio environment, Studio-related JS/CSS assets are loaded.

        Makes no use of the context parameter.
        """
        fragment = Fragment()
        for css_file in get_css_dependencies('style-capa'):
            fragment.add_css_url(staticfiles_storage.url(css_file))
        for js_file in get_js_dependencies('capa'):
            fragment.add_javascript_url(staticfiles_storage.url(js_file))
        fragment.add_content(self.get_html())
        fragment.initialize_js('CapaXBlock')
        return fragment

    def studio_editor_tab_view(self, context=None):
        """
        :param context: The context template is using.
        :return: A rendered HTML for editor template.
        """
        template_name = 'editor.html'
        template_path = os.path.join(self.tabs_templates_dir, template_name)

        if context is None:
            context = {}
        context.update({
            'data': self.data,
            'markdown': self.markdown,
            'enable_latex_compiler': self.use_latex_compiler,
            'is_latex_problem': (self.use_latex_compiler and self.source_code),
        })
        return loader.render_django_template(template_path, context=context)

    @property
    def ajax_url(self):
        """
        Returns the URL for the ajax handler.
        """
        return self.runtime.handler_url(self, 'ajax_handler', '', '').rstrip('/?')

    @XBlock.handler
    def ajax_handler(self, request, suffix=None):
        """
        XBlock handler that wraps `handle_ajax`
        """
        class FileObjForWebobFiles(object):
            """
            Turn Webob cgi.FieldStorage uploaded files into pure file objects.
            Webob represents uploaded files as cgi.FieldStorage objects, which
            have a .file attribute.  We wrap the FieldStorage object, delegating
            attribute access to the .file attribute.  But the files have no
            name, so we carry the FieldStorage .filename attribute as the .name.
            """
            def __init__(self, webob_file):
                self.file = webob_file.file
                self.name = webob_file.filename

            def __getattr__(self, name):
                return getattr(self.file, name)

        # WebOb requests have multiple entries for uploaded files.
        # handle_ajax expects a single entry as a list.
        request_post = MultiDict(request.POST)
        for key in set(request.POST.iterkeys()):
            if hasattr(request.POST[key], "file"):
                request_post[key] = map(FileObjForWebobFiles, request.POST.getall(key))

        response_data = self.handle_ajax(suffix, request_post)
        return Response(response_data, content_type='application/json', charset='UTF-8')

    def handle_ajax(self, dispatch, request_post):
        """
        This is called by courseware.module_render, and to handle AJAX calls.

        Returns a json dictionary:
        { 'progress_changed' : True/False,
          'progress' : 'none'/'in_progress'/'done',
          <other request-specific values here > }
        """
        handlers = {
            'problem_check': self.submit_problem,
            'problem_reset': self.reset_problem,
            'problem_save': self.save_problem,
            'score_update': self.update_score,
            'input_ajax': self.handle_input_ajax,
            'ungraded_response': self.handle_ungraded_response
        }

        _ = self.runtime.service(self, "i18n").ugettext

        generic_error_message = _(
            "We're sorry, there was an error with processing your request. "
            "Please try reloading your page and trying again."
        )

        not_found_error_message = _(
            "The state of this problem has changed since you loaded this page. "
            "Please refresh your page."
        )

        if dispatch not in handlers:
            return 'Error: {} is not a known capa action'.format(dispatch)

        before = self.get_progress()
        before_attempts = self.attempts

        try:
            result = handlers[dispatch](request_post)

        except NotFoundError:
            log.info(
                "Unable to find data when dispatching %s to %s for user %s",
                dispatch,
                self.scope_ids.usage_id,
                self.scope_ids.user_id
            )
            _, _, traceback_obj = sys.exc_info()
            raise ProcessingError(not_found_error_message), None, traceback_obj

        except Exception:
            log.exception(
                "Unknown error when dispatching %s to %s for user %s",
                dispatch,
                self.scope_ids.usage_id,
                self.scope_ids.user_id
            )
            _, _, traceback_obj = sys.exc_info()
            raise ProcessingError(generic_error_message), None, traceback_obj

        after = self.get_progress()
        after_attempts = self.attempts
        progress_changed = (after != before) or (after_attempts != before_attempts)
        curr_score, total_possible = self.get_display_progress()

        result.update({
            'progress_changed': progress_changed,
            'current_score': curr_score,
            'total_possible': total_possible,
            'attempts_used': after_attempts,
        })

        return json.dumps(result, cls=ComplexEncoder)

    @XBlock.json_handler
    def hint_button(self, data, suffix=None):  # pylint: disable=unused-argument
        """
        Hint button handler, returns new html using hint_index from the client.
        """
        hint_index = int(data.get('hint_index', 0))
        return self.get_demand_hint(hint_index)

    @XBlock.json_handler
    def problem_get(self, data, suffix=None):  # pylint: disable=unused-argument
        """
        Return results of get_problem_html, as a simple dict for json-ing.
        { 'html': <the-html> }

        Used if we want to reconfirm we have the right thing e.g. after
        several AJAX calls.
        """
        return {'html': self.get_problem_html(encapsulate=False, submit_notification=True)}

    @XBlock.json_handler
    def problem_show(self, data, suffix=None):  # pylint: disable=unused-argument
        """
        For the "show answer" button.

        Returns the answers and rendered "correct status span" HTML:
            {'answers' : answers, 'correct_status_html': correct_status_span_html}.
            The "correct status span" HTML is injected beside the correct answers
            for radio button and checkmark problems, so that there is a visual
            indication of the correct answers that is not solely based on color
            (and also screen reader text).
        """
        return self.get_answer()

    @property
    def location(self):
        """
        Returns this block's location (usage_key).
        """
        return self.scope_ids.usage_id

    @property
    def category(self):
        """
        Returns this block's category (AKA block_type).
        """
        return self.scope_ids.block_type

    @property
    def display_name_with_default(self):
        """
        Constructs the display name for a CAPA problem.

        Default to the display_name if it isn't None or not an empty string,
        else fall back to problem category.
        """
        if self.display_name is None or not self.display_name.strip():
            return self.category

        return self.display_name

    @property
    def anonymous_student_id(self):
        """
        Returns the anonymous user ID for the current user+course.
        """
        user_service = self.runtime.service(self, 'user')
        if user_service:
            return user_service.get_anonymous_user_id(
                user_service.get_username(),
                text_type(self.runtime.course_id),
            )
        return None

    @property
    def user_is_staff(self):
        """
        Returns true if the current user is a staff user.
        """
        user_service = self.runtime.service(self, 'user')
        return user_service.user_is_staff() if user_service else None

    @property
    def _user_id(self):
        """
        Returns the current numeric user ID
        """
        user_service = self.runtime.service(self, 'user')
        return user_service.get_user_id() if user_service else None

    @property
    def block_seed(self):
        """
        Returns the randomization seed.
        """
        # FIXME Uncertain why we need a block-level seed, when there is a user_state seed too?
        return self._user_id or 0

    @property
    def cache(self):
        """
        Returns the default django cache.
        """
        return django_cache

    @property
    def xqueue_interface(self):
        """
        Returns a dict containing XqueueInterface object, as well as parameters
        for the specific StudentModule.

        Copied from courseware.module_render.get_module_system_for_user
        """
        # TODO: refactor into common repo/code?

        def get_xqueue_callback_url_prefix(request):
            """
            Calculates default prefix based on request, but allows override via settings

            This is separated from get_module_for_descriptor so that it can be called
            by the LMS before submitting background tasks to run.  The xqueue callbacks
            should go back to the LMS, not to the worker.
            """
            prefix = '{proto}://{host}'.format(
                proto=request.META.get('HTTP_X_FORWARDED_PROTO', 'https' if request.is_secure() else 'http'),
                host=request.get_host()
            )
            return settings.XQUEUE_INTERFACE.get('callback_url', prefix)

        def make_xqueue_callback(dispatch='score_update'):
            """
            Returns fully qualified callback URL for external queueing system
            """
            relative_xqueue_callback_url = reverse(
                'xqueue_callback',
                kwargs=dict(
                    course_id=text_type(self.runtime.course_id),
                    userid=text_type(self._user_id),
                    mod_id=text_type(self.location),
                    dispatch=dispatch
                ),
            )
            request = self.runtime.service(self, 'request')
            xqueue_callback_url_prefix = get_xqueue_callback_url_prefix(request)
            return xqueue_callback_url_prefix + relative_xqueue_callback_url

        # Default queuename is course-specific and is derived from the course that
        #   contains the current module.
        # TODO: Queuename should be derived from 'course_settings.json' of each course
        xqueue_default_queuename = self.location.org + '-' + self.location.course

        if settings.XQUEUE_INTERFACE.get('basic_auth') is not None:
            requests_auth = HTTPBasicAuth(*settings.XQUEUE_INTERFACE['basic_auth'])
        else:
            requests_auth = None

        xqueue_interface = XQueueInterface(
            settings.XQUEUE_INTERFACE['url'],
            settings.XQUEUE_INTERFACE['django_auth'],
            requests_auth,
        )

        return {
            'interface': xqueue_interface,
            'construct_callback': make_xqueue_callback,
            'default_queuename': xqueue_default_queuename.replace(' ', '_'),
            'waittime': settings.XQUEUE_WAITTIME_BETWEEN_REQUESTS
        }

    @property
    def problem_types(self):
        """ Low-level problem type introspection for content libraries filtering by problem type """
        try:
            tree = etree.XML(self.data)
        except etree.XMLSyntaxError:
            log.error('Error parsing problem types from xml for capa module {}'.format(self.display_name))
            return None  # short-term fix to prevent errors (TNL-5057). Will be more properly addressed in TNL-4525.
        registered_tags = responsetypes.registry.registered_tags()
        return {node.tag for node in tree.iter() if node.tag in registered_tags}

    @property
    def _filestore(self):
        """
        Creates an os filestore.

        Formerly handled by the CachingDescriptorSystem
        """
        # FIXME -- where should this method live?
        if self.location.course_key.course:
            course_key = self.location.course_key
            # FIXME Is settings.DATA_DIR the same as the modulestore().fs_root?
            root = settings.DATA_DIR / course_key.org / course_key.course / course_key.run
        else:
            root = settings.DATA_DIR / str(self.location.structure['_id'])
        root.makedirs_p()  # create directory if it doesn't exist

        return OSFS(root)

    def can_execute_unsafe_code(self):
        """Pass through to xmodule.util.sandboxing method."""
        return can_execute_unsafe_code(self.runtime.course_id)

    def get_python_lib_zip(self):
        """Pass through to xmodule.util.sandboxing method."""
        return get_python_lib_zip(contentstore, self.runtime.course_id)

    def has_support(self, view, functionality):
        """
        Override the XBlock.has_support method to return appropriate
        value for the multi-device functionality.
        Returns whether the given view has support for the given functionality.
        """
        if functionality == "multi_device":
            types = self.problem_types  # Avoid calculating this property twice
            return types is not None and all(
                responsetypes.registry.get_class_for_tag(tag).multi_device_support
                for tag in types
            )
        return False

    def max_score(self):
        """
        Return the problem's max score
        """
        capa_system = LoncapaSystem(
            ajax_url=None,
            anonymous_student_id=None,
            cache=None,
            can_execute_unsafe_code=None,
            get_python_lib_zip=None,
            DEBUG=None,
            filestore=self._filestore,
            i18n=self.runtime.service(self, "i18n"),
            node_path=None,
            render_template=None,
            seed=None,
            STATIC_URL=None,
            xqueue=None,
            matlab_api_key=None,
        )
        lcp = LoncapaProblem(
            problem_text=self.data,
            id=self.location.html_id(),
            capa_system=capa_system,
            capa_module=self,
            state={},
            seed=1,
            minimal_init=True,
        )
        return lcp.get_max_score()

    def generate_report_data(self, user_state_iterator, limit_responses=None):
        """
        Return a list of student responses to this block in a readable way.

        Arguments:
            user_state_iterator: iterator over UserStateClient objects.
                E.g. the result of user_state_client.iter_all_for_block(block_key)

            limit_responses (int|None): maximum number of responses to include.
                Set to None (default) to include all.

        Returns:
            each call returns a tuple like:
            ("username", {
                           "Question": "2 + 2 equals how many?",
                           "Answer": "Four",
                           "Answer ID": "98e6a8e915904d5389821a94e48babcf_10_1"
            })
        """

        log.error("CATEGORY: %s", self.category)
        if self.category != 'problem':
            raise NotImplementedError()

        if limit_responses == 0:
            # Don't even start collecting answers
            return
        capa_system = LoncapaSystem(
            ajax_url=None,
            anonymous_student_id=self.anonymous_student_id,
            cache=None,
            can_execute_unsafe_code=lambda: None,
            get_python_lib_zip=self.get_python_lib_zip,
            DEBUG=None,
            filestore=self._filestore,
            i18n=self.runtime.service(self, "i18n"),
            node_path=None,
            render_template=None,
            seed=1,
            STATIC_URL=None,
            xqueue=None,
            matlab_api_key=None,
        )
        _ = capa_system.i18n.ugettext

        count = 0
        for user_state in user_state_iterator:

            if 'student_answers' not in user_state.state:
                continue

            lcp = LoncapaProblem(
                problem_text=self.data,
                id=self.location.html_id(),
                capa_system=capa_system,
                # We choose to run without a fully initialized CapaModule
                capa_module=None,
                state={
                    'done': user_state.state.get('done'),
                    'correct_map': user_state.state.get('correct_map'),
                    'student_answers': user_state.state.get('student_answers'),
                    'has_saved_answers': user_state.state.get('has_saved_answers'),
                    'input_state': user_state.state.get('input_state'),
                    'seed': user_state.state.get('seed'),
                },
                seed=user_state.state.get('seed'),
                # extract_tree=False allows us to work without a fully initialized CapaModule
                # We'll still be able to find particular data in the XML when we need it
                extract_tree=False,
            )

            for answer_id, orig_answers in lcp.student_answers.items():
                # Some types of problems have data in lcp.student_answers that isn't in lcp.problem_data.
                # E.g. formulae do this to store the MathML version of the answer.
                # We exclude these rows from the report because we only need the text-only answer.
                if answer_id.endswith('_dynamath'):
                    continue

                if limit_responses and count >= limit_responses:
                    # End the iterator here
                    return

                question_text = lcp.find_question_label(answer_id)
                answer_text = lcp.find_answer_text(answer_id, current_answer=orig_answers)
                correct_answer_text = lcp.find_correct_answer_text(answer_id)

                count += 1
                report = {
                    _("Answer ID"): answer_id,
                    _("Question"): question_text,
                    _("Answer"): answer_text,
                }
                if correct_answer_text is not None:
                    report[_("Correct Answer")] = correct_answer_text
                yield (user_state.username, report)

    @classmethod
    def parse_xml(cls, node, runtime, keys, id_generator):
        """
        Parses OLX into XBlock.

        This method is overridden here to allow parsing legacy OLX, coming from capa XModule.
        XBlock stores all the associated data, fields and children in a XML element inlined into vertical XML file
        XModule stored only minimal data on the element included into vertical XML and used a dedicated "problem"
        folder in OLX to store fields and children.

        If no external data sources are found (file in "problem" folder), it is exactly equivalent to base method
        XBlock.parse_xml. Otherwise this method parses file in "problem" folder (known as definition_xml), applies
        policy.json and updates fields accordingly.
        """
        block = super(CapaXBlock, cls).parse_xml(node, runtime, keys, id_generator)

        cls._apply_translations_to_node_attributes(block, node)
        cls._apply_metadata_and_policy(block, node, runtime)

        return block

    @classmethod
    def _apply_translations_to_node_attributes(cls, block, node):
        """
        Applies metadata translations for attributes stored on an inlined XML element.
        """
        for old_attr, target_attr in cls.metadata_translations.iteritems():
            if old_attr in node.attrib and hasattr(block, target_attr):
                setattr(block, target_attr, node.attrib[old_attr])

    @classmethod
    def _apply_metadata_and_policy(cls, block, node, runtime):
        """
        Attempt to load definition XML from "problem" folder in OLX, than parse it and update block fields
        """
        try:
            definition_xml, _ = cls.load_definition_xml(node, runtime, block.scope_ids.def_id)
        except Exception as err:  # pylint: disable=broad-except
            log.info(
                "Exception %s when trying to load definition xml for block %s - assuming XBlock export format",
                err,
                block
            )
            return

        metadata = cls.load_metadata(definition_xml)
        # TODO: this was copied from DiscussionXBlock, but I don't think CAPA xblocks use policy?
        cls.apply_policy(metadata, runtime.get_policy(block.scope_ids.usage_id))

        for field_name, value in metadata.iteritems():
            if field_name in block.fields:
                setattr(block, field_name, value)
