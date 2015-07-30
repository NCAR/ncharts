from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
import datetime, pytz

class Command(NoArgsCommand):
    def handle_noargs(self, **options):
        today = datetime.date.today() + datetime.timedelta(days=7)
        aged = ClientState.objects.filter(last_save__lt=today)

        for clnt in aged:
            print("pk=%d, dataset=%s, last_save=%s" % \
                (clnt.pk, clnt.dataset, clnt.last_save))

