from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import user_passes_test
from django.contrib.auth.models import User
from django.contrib import messages
from django.utils import timezone
from django.db.models import Count, Q
from datetime import timedelta
from .models import Report
from core.models import Match
from django.contrib.sessions.models import Session

def is_staff(user):
    """
    Check if the user is a staff member.
    """
    return user.is_staff

@user_passes_test(is_staff)
def dashboard(request):
    """
    Displays analytics for signups, matches, and active sessions.
    """
    # User signups
    today = timezone.now().date()
    signups_today = User.objects.filter(date_joined__date=today).count()
    signups_last_7_days = User.objects.filter(date_joined__gte=today - timedelta(days=7)).count()
    total_users = User.objects.count()

    # Matches
    # This logic assumes a match is two-way.
    matches_count = Match.objects.values('user1', 'user2').distinct().count()

    # Active Sessions (users active in the last 30 minutes)
    active_sessions = Session.objects.filter(expire_date__gte=timezone.now()).count()

    # Pending reports
    pending_reports_count = Report.objects.filter(status='pending').count()

    context = {
        'total_users': total_users,
        'signups_today': signups_today,
        'signups_last_7_days': signups_last_7_days,
        'matches_count': matches_count,
        'active_sessions': active_sessions,
        'pending_reports_count': pending_reports_count,
        'is_admin_panel': True, # For base template to show admin nav
    }
    return render(request, 'administration/dashboard.html', context)

@user_passes_test(is_staff)
def report_list(request):
    """
    Lists all user-submitted reports, with filtering by status.
    """
    status_filter = request.GET.get('status', 'pending')
    reports = Report.objects.filter(status=status_filter).select_related('reporter', 'reported_user')

    context = {
        'reports': reports,
        'status_filter': status_filter,
        'is_admin_panel': True,
    }
    return render(request, 'administration/report_list.html', context)

@user_passes_test(is_staff)
def report_detail(request, report_id):
    """
    Displays the details of a specific report and allows status updates.
    """
    report = get_object_or_404(Report, id=report_id)

    if request.method == 'POST':
        new_status = request.POST.get('status')
        admin_notes = request.POST.get('admin_notes')
        if new_status in [choice[0] for choice in Report.STATUS_CHOICES]:
            report.status = new_status
            report.admin_notes = admin_notes
            report.save()
            messages.success(request, "Report status updated successfully.")
            return redirect('administration:report_list')

    context = {
        'report': report,
        'is_admin_panel': True,
    }
    return render(request, 'administration/report_detail.html', context)

@user_passes_test(is_staff)
def suspend_user(request, user_id):
    """
    Suspends a user by setting their account to inactive.
    """
    if request.method == 'POST':
        user_to_suspend = get_object_or_404(User, id=user_id)
        report_id = request.POST.get('report_id')

        if user_to_suspend.is_staff:
            messages.error(request, "Admin accounts cannot be suspended.")
        else:
            user_to_suspend.is_active = False
            user_to_suspend.save()
            messages.success(request, f"User '{user_to_suspend.username}' has been suspended.")

            # Optionally, update the related report status
            if report_id:
                try:
                    report = Report.objects.get(id=report_id)
                    report.status = 'action_taken'
                    report.save()
                except Report.DoesNotExist:
                    pass # Report might have been deleted, fail silently
        
        # Redirect back to the appropriate page
        if report_id:
            return redirect('administration:report_detail', report_id=report_id)
        return redirect('administration:user_detail', user_id=user_id)
    return redirect('administration:dashboard')

@user_passes_test(is_staff)
def reactivate_user(request, user_id):
    """
    Reactivates a suspended user by setting their account to active.
    """
    if request.method == 'POST':
        user_to_reactivate = get_object_or_404(User, id=user_id)
        user_to_reactivate.is_active = True
        user_to_reactivate.save()
        messages.success(request, f"User '{user_to_reactivate.username}' has been reactivated.")
        return redirect('administration:user_detail', user_id=user_id)
    return redirect('administration:dashboard')

@user_passes_test(is_staff)
def user_list(request):
    """
    Lists all users with search and filtering.
    """
    query = request.GET.get('q', '')
    status_filter = request.GET.get('status', 'all')

    users = User.objects.all().order_by('username')

    if query:
        users = users.filter(Q(username__icontains=query) | Q(email__icontains=query))

    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'suspended':
        users = users.filter(is_active=False)

    context = {
        'users': users,
        'query': query,
        'status_filter': status_filter,
        'is_admin_panel': True,
    }
    return render(request, 'administration/user_list.html', context)

@user_passes_test(is_staff)
def user_detail(request, user_id):
    """
    Displays details for a specific user and their report history.
    """
    user = get_object_or_404(User, id=user_id)
    reports_against_user = Report.objects.filter(reported_user=user).select_related('reporter')

    context = {
        'managed_user': user,
        'reports_against_user': reports_against_user,
        'is_admin_panel': True,
    }
    return render(request, 'administration/user_detail.html', context)