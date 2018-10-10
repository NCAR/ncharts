from django.core.management.base import BaseCommand

from ncharts.models import VariableTimes
from ncharts.models import ClientState
from ncharts import views as nc_views

from django.contrib.sessions.models import Session


class Command(BaseCommand):
    def handle(self, **options):

        sessions = Session.objects.all()
        print("#sessions=%d" % len(sessions))

        clnts = ClientState.objects.all()
        print("#clients=%d" % len(clnts))

        clnts_active = set()
        ndeleted = 0

        for sess in sessions:
            sess_dict = sess.get_decoded()

            for sess_key in sess_dict:
                for clnt in clnts:
                    dset = clnt.dataset
                    project = dset.project
                    cid_name = nc_views.client_id_name(
                        project.name, dset.name)

                    if cid_name == sess_key and sess_dict[cid_name] == clnt.pk:
                        clnts_active.add(clnt.pk)
                        break

        dtimes_active = set()
        for clnt in clnts:
            if clnt.pk in clnts_active:
                print("client found in session: pk=%d, dataset=%s" % \
                    (clnt.pk, clnt.dataset))
                # dtimes = clnt.data_times.all()
                # for dt in dtimes:
                #     print("client pk=%d, active data_time, type(dt)=%s, dt.pk=%d" % \
                #             (clnt.pk, type(dt), dt.pk))
                dtimes_active.update(clnt.data_times.all())
            else:
                print("client not found in session: pk=%d, dataset=%s, deleting" % \
                    (clnt.pk, clnt.dataset))
                clnt.delete()
                ndeleted += 1

        print("#clients deleted=%d" % (ndeleted))

        vtimes = VariableTimes.objects.all()
        print("#vtimes=%d" % len(vtimes))

        ndeleted = 0
        for vt in vtimes:
            # print("type vt=%s" % type(vt))
            if vt not in dtimes_active:
                print("VariableTime not found in a client: pk=%d, deleting" % \
                        vt.pk)
                vt.delete()
                ndeleted += 1
        print("#vtimes deleted=%d" % (ndeleted))

