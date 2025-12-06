from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from django.contrib.auth.models import User
from .models import Profile, Course, StudyPreference
from core.models import Match
from administration.models import Report
import requests


# Create your views here.
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("accounts:profile")
    else:
        form = UserCreationForm()
    return render(request, "accounts/signup.html", {"form": form})


def login(request):
    if request.method == "POST":
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            messages.success(request, "Welcome back!")
            return redirect("core:swipe")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout(request):
    auth_logout(request)
    return redirect("home:index")

@login_required
def profile(request):
    # This is now the view-only profile page.
    profile = request.user.profile
    location_name = None

    if profile.latitude and profile.longitude:
        try:
            # Use Nominatim for reverse geocoding. A User-Agent is required by their usage policy.
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={profile.latitude}&lon={profile.longitude}&zoom=10"
            headers = {'User-Agent': 'StudyBuddy/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            
            address = data.get('address', {})
            # Construct a readable location string, preferring city/town, then state, then country.
            parts = [
                address.get('city'),
                address.get('town'),
                address.get('village'),
                address.get('state'),
                address.get('country')
            ]
            location_name = ', '.join(p for p in parts if p)
        except (requests.RequestException, KeyError):
            location_name = "Location details unavailable"

    return render(request, "accounts/profile_view.html", {"profile": profile, "location_name": location_name})

@login_required
def edit_profile(request):
    if request.method == 'POST':
        # --- Handle Full Name ---
        full_name = request.POST.get('full_name', '').strip()
        first_name, last_name = (full_name.split(' ', 1) + [''])[:2]

        # Update User model fields
        request.user.first_name = first_name
        request.user.last_name = last_name
        request.user.save()

        # Update Profile model fields
        profile = request.user.profile
        profile.university = request.POST.get('university', '')
        profile.major = request.POST.get('major', '')
        profile.year_of_study = request.POST.get('year') or None
        profile.bio = request.POST.get('bio', '')
        profile.latitude = request.POST.get('latitude') or None
        profile.longitude = request.POST.get('longitude') or None
        profile.search_radius = request.POST.get('search_radius', 5)

        # --- Handle Privacy Settings ---
        profile.academic_info_visibility = request.POST.get('academic_info_visibility', 'public')
        profile.bio_visibility = request.POST.get('bio_visibility', 'public')
        profile.courses_visibility = request.POST.get('courses_visibility', 'public')
        profile.location_visibility = request.POST.get('location_visibility', 'public')
        profile.save()

        # --- Handle Courses ---
        course_ids = request.POST.getlist('courses')
        profile.courses.set(course_ids)

        # --- Handle Study Preferences ---
        preference_ids = request.POST.getlist('study_preferences')
        profile.study_preferences.set(preference_ids)

        messages.success(request, "Your profile has been updated successfully!")
        return redirect('accounts:profile')

    # --- Prepare data for GET request ---
    profile = request.user.profile
    all_courses = Course.objects.all()
    all_study_preferences = StudyPreference.objects.all()
    context = {
        'profile': profile,
        'all_courses': all_courses,
        'all_study_preferences': all_study_preferences,
    }
    return render(request, "accounts/profile_edit.html", context)

@login_required
def view_profile(request, username):
    """
    Displays a user's profile to another user, respecting privacy settings.
    """
    profile_user = get_object_or_404(User, username=username)

    # Prevent users from viewing their own profile via this public URL; redirect to their main profile page.
    if profile_user == request.user:
        return redirect('accounts:profile')

    profile = profile_user.profile
    
    # Determine the relationship with the viewing user
    # A match is reciprocal. Check if user1 liked user2 AND user2 liked user1.
    match_exists_1 = Match.objects.filter(user1=request.user, user2=profile_user).exists()
    match_exists_2 = Match.objects.filter(user1=profile_user, user2=request.user).exists()
    is_match = match_exists_1 and match_exists_2

    location_name = None
    # Check if location is visible before trying to geocode it
    can_view_location = (profile.location_visibility == 'public') or (profile.location_visibility == 'matches' and is_match)
    if can_view_location and profile.latitude and profile.longitude:
        try:
            url = f"https://nominatim.openstreetmap.org/reverse?format=json&lat={profile.latitude}&lon={profile.longitude}&zoom=10"
            headers = {'User-Agent': 'StudyBuddy/1.0'}
            response = requests.get(url, headers=headers, timeout=5)
            response.raise_for_status()
            data = response.json()
            address = data.get('address', {})
            parts = [address.get('city'), address.get('town'), address.get('state')]
            location_name = ', '.join(p for p in parts if p)
        except (requests.RequestException, KeyError):
            location_name = "Location details unavailable"

    context = {'profile': profile, 'is_match': is_match, 'location_name': location_name}
    return render(request, 'accounts/public_profile.html', context)

@login_required
def report_user(request, username):
    """
    Allows a user to report another user.
    """
    reported_user = get_object_or_404(User, username=username)
    if request.method == 'POST':
        reason = request.POST.get('reason')
        if reason:
            Report.objects.create(
                reporter=request.user,
                reported_user=reported_user,
                reason=reason
            )
            messages.success(request, f"Your report against {username} has been submitted. Thank you for helping keep our community safe.")
            return redirect('accounts:view_profile', username=username)
        else:
            messages.error(request, "A reason is required to submit a report.")

    context = {'reported_user': reported_user}
    return render(request, 'accounts/report_user.html', context)
