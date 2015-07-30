from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
from ncharts import views as nc_views

from django.contrib.sessions.models import Session

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        sessions = Session.objects.all()
        print("#sessions=%d" % len(sessions))

        for sess in sessions:
            print("session=%s" % str(sess))
            sess_dict = sess.get_decoded()
            # print("session keys=%s" % (repr([k for k in sess_dict.keys()])))

            for sessk in sess_dict:
                if len(sessk) > 5 and sessk[0:5] == "pdid_":
                    print("  sessk=%s, client_id=%d" % (sessk, sess_dict[sessk]))


