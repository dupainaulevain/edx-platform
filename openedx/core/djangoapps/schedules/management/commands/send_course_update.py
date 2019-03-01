from openedx.core.djangoapps.schedules.management.commands import SendEmailBaseCommand
from openedx.core.djangoapps.schedules.tasks import ScheduleCourseUpdate


class Command(SendEmailBaseCommand):
    help = """
            Sends out weekly course highlight emails on a hard-coded list of days.
            The updates are sent weekly until 77 days after enrollment,
            and then stop.
            """

    async_send_task = ScheduleCourseUpdate
    log_prefix = 'Course Update'
    offsets = xrange(-7, -77, -7)
