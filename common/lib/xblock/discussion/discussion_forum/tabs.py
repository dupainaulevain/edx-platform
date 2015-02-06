from django.utils.translation import ugettext_noop

from courseware.tabs import EnrolledTab
from xmodule.tabs import DynamicXBlockTabMixin, FeatureFlagTabMixin


_ = lambda text: text


class DiscussionXBlockTab(FeatureFlagTabMixin, DynamicXBlockTabMixin, EnrolledTab):
    """
    A tab that shows discussion forum UI via DiscussionCourse XBlock
    """
    type = 'discussion-xblock'
    title = ugettext_noop('DiscussionXBlock')
    is_hideable = True
    is_default = False

    target_xblock = 'discussion-course'
    feature_flag = 'ENABLE_DISCUSSION_SERVICE'

    def __init__(self, tab_dict=None):
        super(DiscussionXBlockTab, self).__init__(tab_dict)

        self.link_func = lambda course, reverse_url_func: reverse_url_func(
            'xblock_tab', args=[course.id.to_deprecated_string(), self.target_xblock]
        )

