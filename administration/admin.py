from django.contrib import admin
from .models import Report

# Register your models here.
@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('reported_user', 'reporter', 'status', 'timestamp')
    list_filter = ('status',)
    search_fields = ('reporter__username', 'reported_user__username', 'reason')
    readonly_fields = ('reporter', 'reported_user', 'reason', 'timestamp')
    list_editable = ('status',)
    date_hierarchy = 'timestamp'
