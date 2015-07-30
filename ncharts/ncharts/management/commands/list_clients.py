from django.core.management.base import NoArgsCommand

from ncharts.models import ClientState
from ncharts import views as nc_views

from django.contrib.sessions.models import Session

class Command(NoArgsCommand):
    def handle_noargs(self, **options):


        sessions = Session.objects.all()
        print("#sessions=%d" % len(sessions))
        clnts = ClientState.objects.all()

        active = {}

        for sess in sessions:
            sess_dict = sess.get_decoded()

            for sess_key in sess_dict:
                for clnt in clnts:
                    dset = clnt.dataset
                    project = dset.project
                    cid_name = nc_views.client_id_name(
                        project.name, dset.name)

                    if cid_name == sess_key and sess_dict[cid_name] == clnt.pk:
                        active[clnt.pk] = str(sess)
                        break

        for clnt in clnts:
            if clnt.pk in active:
                print("project=%s, dataset=%s, pk=%d, found in session %s" % \
                    (clnt.dataset.project, clnt.dataset, clnt.pk, active[clnt.pk]))
            else:
                print("project=%s, dataset=%s, pk=%d, session not found with key='%s' not" % \
                    (clnt.dataset.project, clnt.dataset, clnt.pk, nc_views.client_id_name(
                        clnt.dataset.project.name, clnt.dataset.name)))

        print("#clients=%d, #unattached=%d" % (len(clnts),len(clnts)-len(active)))


