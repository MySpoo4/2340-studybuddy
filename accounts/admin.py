from django.contrib import admin
from .models import Profile, Course, StudyPreference

class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

admin.site.register(Profile)
admin.site.register(Course, CourseAdmin)
admin.site.register(StudyPreference)