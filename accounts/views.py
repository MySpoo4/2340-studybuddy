from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login as auth_login, logout as auth_logout
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib import messages
from .models import Profile, Course, StudyPreference


# Create your views here.
def signup(request):
    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            auth_login(request, user)
            messages.success(request, "Account created successfully!")
            return redirect("accounts.profile")
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
            return redirect("core.swipe")
        else:
            messages.error(request, "Invalid username or password.")
    else:
        form = AuthenticationForm()
    return render(request, "accounts/login.html", {"form": form})


@login_required
def logout(request):
    auth_logout(request)
    return redirect("home.index")

@login_required
def profile(request):
    # This is now the view-only profile page.
    profile = request.user.profile
    return render(request, "accounts/profile_view.html", {"profile": profile})

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
        profile.search_radius = request.POST.get('search_radius', 5)
        profile.save()

        # --- Handle Courses ---
        course_ids = request.POST.getlist('courses')
        profile.courses.set(course_ids)

        # --- Handle Study Preferences ---
        preference_ids = request.POST.getlist('study_preferences')
        profile.study_preferences.set(preference_ids)

        messages.success(request, "Your profile has been updated successfully!")
        return redirect('accounts.profile')

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
