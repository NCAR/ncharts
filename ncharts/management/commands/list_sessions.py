from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
from ncharts import views as nc_views

import datetime, pytz

from django.contrib.sessions.models import Session

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        tnow = datetime.datetime.now(tz=pytz.utc)
        sessions = Session.objects.all()
        print("#sessions=%d" % len(sessions))

        for sess in sessions:
            td = (sess.expire_date - tnow).total_seconds() / 86400.
            print("session=%s, expire=%s, in %.1f days" % (str(sess), sess.expire_date.isoformat(), td))
            sess_dict = sess.get_decoded()
            # print("session keys=%s" % (repr([k for k in sess_dict.keys()])))

            for sessk in sess_dict:
                if len(sessk) > 5 and sessk[0:5] == "pdid_":
                    exists = ClientState.objects.filter(pk=sess_dict[sessk]).exists()
                    print("  key='%s', client pk=%d, exists=%s" % (sessk, sess_dict[sessk], exists))


