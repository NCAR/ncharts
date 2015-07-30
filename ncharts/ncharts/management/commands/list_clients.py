from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
from ncharts import views as nc_views

from django.contrib.sessions.models import Session

class Command(NoArgsCommand):
    def handle_noargs(self, **options):

        clnts = ClientState.objects.all()

        sessions = Session.objects.all()
        print("#sessions=%d" % len(sessions))

        active = set()
        n_inactive = 0

        for sess in sessions:
            sess_dict = sess.get_decoded()

            for clnt in clnts:
                dset = clnt.dataset
                project = dset.project
                cid_name = nc_views.client_id_name(
                    project.name, dset.name)

                if cid_name in sess_dict and sess_dict[cid_name] == clnt.pk:
                    active.add(clnt.pk)
                    break
        for clnt in clnts:
            if clnt.pk in active:
                print("client found in session: pk=%d, dataset=%s" % \
                    (clnt.pk, clnt.dataset))
            else:
                print("client not found in session: pk=%d, dataset=%s" % \
                    (clnt.pk, clnt.dataset))
                n_inactive += 1

        print("#clients=%d, #in-active=%d" % (len(clnts),n_inactive))


