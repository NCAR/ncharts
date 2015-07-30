from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
import datetime, pytz

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        clnts = ClientState.objects.all()

        for clnt in clnts:
            if not clnt.last_save:
                clnt.last_save = today
                clnt.save()
                print("saved, clnt.pk=%d" % (clnt.pk))

