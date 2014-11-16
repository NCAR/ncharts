from django.contrib import admin
from ncharts.models import Project, Platform, Dataset

class ProjectAdmin(admin.ModelAdmin):
    pass

class PlatformAdmin(admin.ModelAdmin):
    pass

class DatasetAdmin(admin.ModelAdmin):
    pass

admin.site.register(Project,ProjectAdmin)

admin.site.register(Platform,PlatformAdmin)

admin.site.register(Dataset,DatasetAdmin)

