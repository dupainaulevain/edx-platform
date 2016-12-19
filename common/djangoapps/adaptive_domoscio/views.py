"""
Adaptive Domoscio
"""
import calendar
import datetime
import json

from django.contrib.auth.decorators import login_required
from django.core.urlresolvers import reverse
from django.http import HttpResponse
from django.views.decorators.csrf import ensure_csrf_cookie
from xmodule.modulestore.django import modulestore
from opaque_keys.edx.locator import BlockUsageLocator
from xmodule.modulestore.search import path_to_location, navigation_index


@login_required
@ensure_csrf_cookie
def revisions(request):
    """
    Return a JSON list of all revisions for a user. Each revision includes a name, due date, and URL.
    """
    user = request.user

    revisions = _get_pending_revisions(user)
    json_revisions = json.dumps(revisions)

    return HttpResponse(json_revisions)


def _get_pending_revisions(user):
    """
    Returns information about each problem that needs revision for a given user, including a display name, the due date
    of the revision, and a courseware URL.
    """
    # TODO: Grab all of the AdaptiveLibraryContentModules for the user.
    #       to the Domoscio API.
    serialized_locators = [
        'block-v1:asdf+asdf+asdf+type@problem+block@9adc878ed55943caa7d4b4cd48e52752',
        'block-v1:asdf+asdf+asdf+type@problem+block@0c4c0798cf3847ae9c706cdcb9442c62',
    ]

    locators = map(BlockUsageLocator.from_string, serialized_locators)

    revision_data = []
    for locator in locators:
        # Resolve the courseware URL for the revision xblock.
        (
            course_key, chapter, section, vertical_unused,
            position, final_target_id_unused
        ) = path_to_location(modulestore(), locator)

        url = reverse(
            'courseware_position',
            args=(unicode(course_key), chapter, section, navigation_index(position))
        )

        xblock = modulestore().get_item(locator)
        # TODO: Make a call to the Domoscio API to get the display information for the xblock.
        revision_data.append({
            'name': 'testname',  # xblock.name,
            'due_date': calendar.timegm(datetime.date(2017, 1, 1).timetuple()),  # xblock.due,
            'url': url,
        })

    return revision_data
