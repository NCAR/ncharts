from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
import datetime, pytz

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        old = datetime.date.today() - datetime.timedelta(days=14)
        aged = ClientState.objects.filter(last_save__lt=old)

        for clnt in aged:
            print("deleting, pk=%d, dataset=%s, last_save=%s" % \
                (clnt.pk, clnt.dataset, clnt.last_save))
            clnt.delete()

