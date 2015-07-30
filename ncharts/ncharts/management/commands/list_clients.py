from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
import datetime, pytz

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        clnts = ClientState.objects.all()

        for clnt in clnts:
            print("pk=%d, dataset=%s, last_save=%s" % \
                (clnt.pk, clnt.dataset, clnt.last_save))

