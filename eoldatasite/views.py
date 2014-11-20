from django.http import HttpResponse, Http404

def index(request):
    return HttpResponse("<a href='ncharts'>ncharts</a>")
