from django.contrib import admin
from .models import Profile, Course, StudyPreference

class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'university', 'major')
    search_fields = ('user__username', 'university', 'major')

class CourseAdmin(admin.ModelAdmin):
    list_display = ('code', 'name')
    search_fields = ('code', 'name')

admin.site.register(Profile, ProfileAdmin)
admin.site.register(Course, CourseAdmin)
admin.site.register(StudyPreference)