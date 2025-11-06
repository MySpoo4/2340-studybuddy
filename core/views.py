from django.shortcuts import render, get_object_or_404, redirect

from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from math import radians, sin, cos, sqrt, atan2
from django.db.models import Q, Count
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib import messages
from django.utils import timezone
from django.conf import settings
from .models import Swipe, Match, Message, StudySession
from accounts.models import Profile

import json
from datetime import datetime, timedelta
import os

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


# Create your views here.
def haversine(lat1, lon1, lat2, lon2):
    """Calculate the distance between two points on Earth in kilometers."""
    R = 6371  # Radius of Earth in kilometers
    dLat = radians(lat2 - lat1)
    dLon = radians(lon2 - lon1)
    lat1 = radians(lat1)
    lat2 = radians(lat2)

    a = sin(dLat / 2)**2 + cos(lat1) * cos(lat2) * sin(dLon / 2)**2
    c = 2 * atan2(sqrt(a), sqrt(1 - a))
    distance = R * c
    return distance


@login_required
def swipe_view(request):
    current_user = request.user
    
    # Users the current user has already swiped on
    swiped_users_ids = Swipe.objects.filter(swiper=current_user).values_list('swiped_id', flat=True)

    # Users who have already matched with the current user
    matched_users_ids_raw = Match.objects.filter(Q(user1=current_user) | Q(user2=current_user)).values_list(
        'user1_id', 'user2_id'
    )
    # Flatten the list of tuples and remove duplicates
    matched_users_ids = {item for sublist in matched_users_ids_raw for item in sublist if item != current_user.id}

    # Exclude self, users already swiped on, and users already matched with
    exclude_ids = set(swiped_users_ids) | matched_users_ids | {current_user.id}

    # --- Enhanced Compatibility Scoring Logic ---
    # Get all potential users, excluding those already swiped, matched, or self.
    potential_matches_qs = User.objects.exclude(id__in=exclude_ids).select_related('profile').prefetch_related('profile__courses', 'profile__study_preferences')

    # Get the current user's courses and preferences for comparison
    current_user_courses = set(current_user.profile.courses.values_list('id', flat=True))
    current_user_preferences = set(current_user.profile.study_preferences.values_list('id', flat=True))

    # Calculate a compatibility score for each user in Python
    scored_users = []
    for user in potential_matches_qs:
        user_courses = set(user.profile.courses.values_list('id', flat=True))
        user_preferences = set(user.profile.study_preferences.values_list('id', flat=True))

        common_courses_count = len(current_user_courses.intersection(user_courses))
        common_preferences_count = len(current_user_preferences.intersection(user_preferences))

        # Score: 2 points for each common course, 1 for each common preference
        score = (common_courses_count * 2) + common_preferences_count
        scored_users.append({'user': user, 'score': score})

    # Sort users by their score in descending order
    sorted_users = sorted(scored_users, key=lambda x: x['score'], reverse=True)
    potential_matches = [item['user'] for item in sorted_users]

    # --- Get count of users who liked the current user ---
    # Find IDs of users who have liked the current user
    likers_ids = Swipe.objects.filter(
        swiped=current_user, 
        liked=True
    ).values_list('swiper_id', flat=True)

    # Find IDs of users the current user has already swiped on
    already_swiped_ids = Swipe.objects.filter(swiper=current_user).values_list('swiped_id', flat=True)

    # The count is users who liked us, but whom we haven't swiped on yet.
    likes_you_count = len(set(likers_ids) - set(already_swiped_ids))

    context = {
        'potential_matches': list(potential_matches),
        'likes_you_count': likes_you_count,
    }
    return render(request, "core/swipe.html", context)


@login_required
def matches_view(request):
    current_user = request.user
    
    # Get all matches where the current user is either user1 or user2
    user_matches = Match.objects.filter(Q(user1=current_user) | Q(user2=current_user)).select_related('user1__profile', 'user2__profile')
    
    # Mark all unseen matches as notified for the current user upon visiting the page
    Match.objects.filter(user1=current_user, user1_notified=False).update(user1_notified=True)
    Match.objects.filter(user2=current_user, user2_notified=False).update(user2_notified=True)
    
    current_user_profile = current_user.profile
    matched_profiles_with_data = []
    
    for match in user_matches:
        # Determine the other user in the match
        other_user = match.user1 if match.user2 == current_user else match.user2
        profile_data = {'profile': other_user.profile, 'distance': None, 'eta': None, 'match_id': match.id}

        # Calculate distance and ETA if both users have locations set
        if current_user_profile.latitude and current_user_profile.longitude and other_user.profile.latitude and other_user.profile.longitude:
            distance = haversine(
                current_user_profile.latitude, current_user_profile.longitude,
                other_user.profile.latitude, other_user.profile.longitude
            )
            profile_data['distance'] = round(distance, 2)
            # Calculate simple ETA assuming average speed of 50 km/h
            eta_minutes = (distance / 50) * 60
            profile_data['eta'] = round(eta_minutes)

        matched_profiles_with_data.append(profile_data)

    context = {
        'matched_profiles_data': matched_profiles_with_data,
        'current_user_profile': current_user_profile,
    }
    return render(request, "core/matches.html", context)


@login_required
def swipe_action_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            swiped_user_id = data.get('swiped_user_id')
            liked = data.get('liked')  # True for 'like', False for 'pass'
        except (json.JSONDecodeError, KeyError):
            return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

        swiper = request.user
        swiped_user = get_object_or_404(User, id=swiped_user_id)

        # Prevent swiping on oneself
        if swiper == swiped_user:
            return JsonResponse({'status': 'error', 'message': 'Cannot swipe on yourself'}, status=400)

        # Create or update the swipe
        swipe, created = Swipe.objects.update_or_create(
            swiper=swiper,
            swiped=swiped_user,
            defaults={'liked': liked}
        )

        is_match = False
        match_profile = None

        if liked:
            # Check if the other user has liked back
            try:
                reverse_swipe = Swipe.objects.get(swiper=swiped_user, swiped=swiper, liked=True)
                # It's a match!
                # To avoid duplicate matches, we order by username to store consistently
                user1, user2 = sorted([swiper, swiped_user], key=lambda u: u.username)
                match, created = Match.objects.get_or_create(user1=user1, user2=user2) # This will now have the new notified fields as False by default

                if created:
                    is_match = True
                    match_profile = swiped_user.profile
                    # The swiper is notified immediately by this response.
                    if swiper == match.user1:
                        match.user1_notified = True
                    else:
                        match.user2_notified = True
                    match.save()


            except Swipe.DoesNotExist:
                # Not a match yet
                pass

        if is_match:
            # Render the match popup content
            popup_html = render_to_string('core/match_popup.html', {
                'match_profile': match_profile,
                'current_user_profile': swiper.profile,
                'match_id': match.id,
            }, request=request)
            return JsonResponse({'status': 'match', 'popup_html': popup_html})

        return JsonResponse({'status': 'success'})

    return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)


@login_required
def check_new_matches_view(request):
    """
    API endpoint for the client to poll for new matches they haven't been notified about.
    """
    current_user = request.user

    # Count all matches where the current user is involved and has not been notified yet.
    new_matches_count = Match.objects.filter(
        (Q(user1=current_user) & Q(user1_notified=False)) |
        (Q(user2=current_user) & Q(user2_notified=False))
    ).count()

    # --- Also get count of users who liked the current user for real-time update ---
    likers_ids = Swipe.objects.filter(
        swiped=current_user, 
        liked=True
    ).values_list('swiper_id', flat=True)
    already_swiped_ids = Swipe.objects.filter(
        swiper=current_user
    ).values_list('swiped_id', flat=True)
    likes_you_count = len(set(likers_ids) - set(already_swiped_ids))
    
    # --- Also get count of unread messages ---
    unread_messages_count = Message.objects.filter(
        match__in=Match.objects.filter(Q(user1=current_user) | Q(user2=current_user)),
        is_read=False
    ).exclude(sender=current_user).count()

    response = JsonResponse({
        'status': 'success',
        'new_matches_count': new_matches_count,
        'likes_you_count': likes_you_count,
        'unread_messages_count': unread_messages_count,
    })
    
    # Add cache-control headers to prevent the browser from caching this API response.
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response


@login_required
def likes_you_view(request):
    """
    Displays a page of users who have swiped right on the current user.
    """
    current_user = request.user

    # Find IDs of users who have liked the current user
    likers_ids = Swipe.objects.filter(
        swiped=current_user, 
        liked=True
    ).values_list('swiper_id', flat=True)

    # Find IDs of users the current user has already swiped on
    already_swiped_ids = Swipe.objects.filter(swiper=current_user).values_list('swiped_id', flat=True)

    # We want to show users who liked us, but whom we haven't swiped on yet.
    users_to_show_ids = set(likers_ids) - set(already_swiped_ids)

    # Fetch the full user/profile objects
    users_who_liked_you = User.objects.filter(id__in=users_to_show_ids).select_related('profile').prefetch_related('profile__courses', 'profile__study_preferences')

    context = {'users_who_liked_you': users_who_liked_you}
    return render(request, "core/likes_you.html", context)


@login_required
def inbox_view(request):
    """Displays a list of all conversations (matches)."""
    current_user = request.user
    matches = Match.objects.filter(
        Q(user1=current_user) | Q(user2=current_user)
    ).select_related('user1__profile', 'user2__profile').prefetch_related('messages').order_by('-timestamp')

    # Annotate each match with the last message for sorting and display
    matches_with_last_message = []
    for match in matches:
        last_message = match.messages.last()
        matches_with_last_message.append({
            'match': match,
            'last_message': last_message
        })
    
    # Sort conversations by the timestamp of the last message, descending.
    matches_with_last_message.sort(key=lambda x: x['last_message'].timestamp if x['last_message'] else x['match'].timestamp, reverse=True)

    return render(request, "core/inbox.html", {'matches_data': matches_with_last_message})


@login_required
def chat_room_view(request, match_id):
    """Displays the chat room for a specific match."""
    current_user = request.user
    
    # A single, robust query to get the match and ensure the user is part of it.
    match = get_object_or_404(
        Match.objects.select_related('user1', 'user2'), 
        Q(id=match_id) & (Q(user1=current_user) | Q(user2=current_user))
    )
    
    # Mark messages from the other user as read upon entering the chat.
    Message.objects.filter(
        match=match, 
        is_read=False
    ).exclude(sender=current_user).update(is_read=True)
    
    context = {
        'match': match,
        'other_user': match.user2 if match.user1 == current_user else match.user1,
    }
    return render(request, "core/chat_room.html", context)


@login_required
def fetch_messages_view(request, match_id):
    """API endpoint to fetch messages for a chat room."""
    current_user = request.user
    # Ensure the user is part of the match
    get_object_or_404(Match, Q(id=match_id) & (Q(user1=current_user) | Q(user2=current_user)))

    messages = Message.objects.filter(match_id=match_id).select_related('sender').order_by('timestamp')
    
    messages_data = [{
        'sender_id': msg.sender.id,
        'content': msg.content,
        'timestamp': timezone.localtime(msg.timestamp).strftime('%b %d, %I:%M %p')
    } for msg in messages]

    return JsonResponse({'messages': messages_data})


@login_required
def send_message_view(request, match_id):
    """API endpoint to send a message."""
    if request.method != 'POST':
        return JsonResponse({'status': 'error', 'message': 'Invalid request method'}, status=405)

    current_user = request.user
    match = get_object_or_404(Match, Q(id=match_id) & (Q(user1=current_user) | Q(user2=current_user)))

    try:
        data = json.loads(request.body)
        content = data.get('content', '').strip()
    except (json.JSONDecodeError, KeyError):
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    if not content:
        return JsonResponse({'status': 'error', 'message': 'Message content cannot be empty'}, status=400)

    Message.objects.create(
        match=match,
        sender=current_user,
        content=content
    )

    # Update the match's timestamp to bring it to the top of the inbox
    match.save()

    return JsonResponse({'status': 'success'})


# Google Calendar OAuth configuration
SCOPES = ['https://www.googleapis.com/auth/calendar']
BASE_URL = os.environ.get('GOOGLE_CALENDAR_BASE_URL', 'http://localhost:8000').rstrip('/')
REDIRECT_URI = f'{BASE_URL}/app/study-sessions/google-calendar/callback/'
CLIENT_ID = os.environ.get('GOOGLE_CALENDAR_CLIENT_ID', '')
CLIENT_SECRET = os.environ.get('GOOGLE_CALENDAR_CLIENT_SECRET', '')
# Allow insecure transport for localhost (set to '1' for development, '0' or unset for production)
OAUTHLIB_INSECURE_TRANSPORT = os.environ.get('OAUTHLIB_INSECURE_TRANSPORT', '0')


def get_google_calendar_credentials(profile):
    """Get valid Google Calendar credentials for a user profile."""
    if not profile.google_calendar_refresh_token:
        return None
    
    creds = Credentials(
        token=profile.google_calendar_access_token,
        refresh_token=profile.google_calendar_refresh_token,
        token_uri='https://oauth2.googleapis.com/token',
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET
    )
    
    # Refresh token if expired
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        profile.google_calendar_access_token = creds.token
        profile.google_calendar_token_expiry = creds.expiry
        profile.save()
    
    return creds


@login_required
def study_sessions_list(request):
    """Display all study sessions the user is involved in."""
    current_user = request.user
    
    # Sessions created by the user
    created_sessions = StudySession.objects.filter(creator=current_user).order_by('start_time')
    
    # Sessions where the user is a participant
    participant_sessions = StudySession.objects.filter(participants=current_user).exclude(creator=current_user).order_by('start_time')
    
    # Check if user has Google Calendar connected
    profile = current_user.profile
    has_google_calendar = bool(profile.google_calendar_refresh_token)
    
    context = {
        'created_sessions': created_sessions,
        'participant_sessions': participant_sessions,
        'has_google_calendar': has_google_calendar,
    }
    return render(request, 'core/study_sessions_list.html', context)


@login_required
def study_session_create(request):
    """Create a new study session."""
    current_user = request.user
    
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '').strip()
        start_time_str = request.POST.get('start_time', '')
        end_time_str = request.POST.get('end_time', '')
        location = request.POST.get('location', '').strip()
        latitude = request.POST.get('latitude') or None
        longitude = request.POST.get('longitude') or None
        participant_ids = request.POST.getlist('participants')
        sync_to_calendar = request.POST.get('sync_to_calendar') == 'on'
        
        # Validation
        if not title or not start_time_str or not end_time_str or not location:
            messages.error(request, 'Please fill in all required fields.')
            return redirect('core:study_session_create')
        
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            messages.error(request, 'Invalid date/time format.')
            return redirect('core:study_session_create')
        
        # Make timezone-aware if needed
        from django.utils import timezone as tz
        if start_time.tzinfo is None:
            start_time = tz.make_aware(start_time)
        if end_time.tzinfo is None:
            end_time = tz.make_aware(end_time)
        
        if end_time <= start_time:
            messages.error(request, 'End time must be after start time.')
            return redirect('core:study_session_create')
        
        # Create the study session
        session = StudySession.objects.create(
            creator=current_user,
            title=title,
            description=description,
            start_time=start_time,
            end_time=end_time,
            location=location,
            latitude=float(latitude) if latitude else None,
            longitude=float(longitude) if longitude else None,
        )
        
        # Add participants
        if participant_ids:
            participants = User.objects.filter(id__in=participant_ids)
            session.participants.set(participants)
        
        # Sync to Google Calendar if requested
        if sync_to_calendar:
            profile = current_user.profile
            if profile.google_calendar_refresh_token:
                event_id = sync_session_to_google_calendar(session, profile)
                if event_id:
                    session.google_calendar_event_id = event_id
                    session.save()
                    messages.success(request, 'Study session created and synced to Google Calendar!')
                else:
                    messages.warning(request, 'Study session created, but failed to sync to Google Calendar.')
            else:
                messages.warning(request, 'Study session created. Please connect Google Calendar to sync.')
        else:
            messages.success(request, 'Study session created successfully!')
        
        return redirect('core:study_sessions_list')
    
    # GET request - show form
    # Get user's matches to invite as participants
    user_matches = Match.objects.filter(Q(user1=current_user) | Q(user2=current_user)).select_related('user1__profile', 'user2__profile')
    potential_participants = []
    for match in user_matches:
        other_user = match.user1 if match.user2 == current_user else match.user2
        potential_participants.append(other_user)
    
    profile = current_user.profile
    has_google_calendar = bool(profile.google_calendar_refresh_token)
    
    context = {
        'potential_participants': potential_participants,
        'has_google_calendar': has_google_calendar,
    }
    return render(request, 'core/study_session_create.html', context)


@login_required
def study_session_edit(request, session_id):
    """Edit an existing study session."""
    session = get_object_or_404(StudySession, id=session_id, creator=request.user)
    
    if request.method == 'POST':
        session.title = request.POST.get('title', '').strip()
        session.description = request.POST.get('description', '').strip()
        start_time_str = request.POST.get('start_time', '')
        end_time_str = request.POST.get('end_time', '')
        session.location = request.POST.get('location', '').strip()
        session.latitude = float(request.POST.get('latitude')) if request.POST.get('latitude') else None
        session.longitude = float(request.POST.get('longitude')) if request.POST.get('longitude') else None
        participant_ids = request.POST.getlist('participants')
        sync_to_calendar = request.POST.get('sync_to_calendar') == 'on'
        
        try:
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
        except ValueError:
            messages.error(request, 'Invalid date/time format.')
            return redirect('core:study_session_edit', session_id=session_id)
        
        # Make timezone-aware if needed
        from django.utils import timezone as tz
        if start_time.tzinfo is None:
            start_time = tz.make_aware(start_time)
        if end_time.tzinfo is None:
            end_time = tz.make_aware(end_time)
        
        session.start_time = start_time
        session.end_time = end_time
        
        if session.end_time <= session.start_time:
            messages.error(request, 'End time must be after start time.')
            return redirect('core:study_session_edit', session_id=session_id)
        
        session.save()
        
        # Update participants
        if participant_ids:
            participants = User.objects.filter(id__in=participant_ids)
            session.participants.set(participants)
        
        # Sync to Google Calendar
        if sync_to_calendar:
            profile = request.user.profile
            if profile.google_calendar_refresh_token:
                if session.google_calendar_event_id:
                    # Update existing event
                    event_id = update_google_calendar_event(session, profile)
                else:
                    # Create new event
                    event_id = sync_session_to_google_calendar(session, profile)
                    if event_id:
                        session.google_calendar_event_id = event_id
                        session.save()
                if event_id:
                    messages.success(request, 'Study session updated and synced to Google Calendar!')
                else:
                    messages.warning(request, 'Study session updated, but failed to sync to Google Calendar.')
            else:
                messages.warning(request, 'Study session updated. Please connect Google Calendar to sync.')
        else:
            messages.success(request, 'Study session updated successfully!')
        
        return redirect('core:study_sessions_list')
    
    # GET request - show form
    user_matches = Match.objects.filter(Q(user1=request.user) | Q(user2=request.user)).select_related('user1__profile', 'user2__profile')
    potential_participants = []
    for match in user_matches:
        other_user = match.user1 if match.user2 == request.user else match.user2
        potential_participants.append(other_user)
    
    profile = request.user.profile
    has_google_calendar = bool(profile.google_calendar_refresh_token)
    
    context = {
        'session': session,
        'potential_participants': potential_participants,
        'has_google_calendar': has_google_calendar,
    }
    return render(request, 'core/study_session_edit.html', context)


@login_required
def study_session_delete(request, session_id):
    """Delete a study session."""
    session = get_object_or_404(StudySession, id=session_id, creator=request.user)
    
    if request.method == 'POST':
        # Delete from Google Calendar if synced
        if session.google_calendar_event_id:
            profile = request.user.profile
            if profile.google_calendar_refresh_token:
                delete_google_calendar_event(session, profile)
        
        session.delete()
        messages.success(request, 'Study session deleted successfully!')
        return redirect('core:study_sessions_list')
    
    context = {'session': session}
    return render(request, 'core/study_session_delete.html', context)


@login_required
def google_calendar_authorize(request):
    """Initiate Google Calendar OAuth flow."""
    # Set insecure transport if configured in environment
    if OAUTHLIB_INSECURE_TRANSPORT == '1':
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    if not CLIENT_ID or not CLIENT_SECRET:
        messages.error(request, 'Google Calendar integration is not configured. Please contact the administrator.')
        return redirect('core:study_sessions_list')
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES
    )
    flow.redirect_uri = REDIRECT_URI
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )
    
    # Store state in session
    request.session['google_calendar_oauth_state'] = state
    
    return redirect(authorization_url)


@login_required
def google_calendar_callback(request):
    """Handle Google Calendar OAuth callback."""
    # Set insecure transport if configured in environment
    if OAUTHLIB_INSECURE_TRANSPORT == '1':
        os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
    
    state = request.session.get('google_calendar_oauth_state')
    if not state or state != request.GET.get('state'):
        messages.error(request, 'Invalid OAuth state. Please try again.')
        return redirect('core:study_sessions_list')
    
    if 'error' in request.GET:
        messages.error(request, 'Google Calendar authorization was cancelled.')
        return redirect('core:study_sessions_list')
    
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [REDIRECT_URI]
            }
        },
        scopes=SCOPES,
        state=state
    )
    flow.redirect_uri = REDIRECT_URI
    
    authorization_response = request.build_absolute_uri()
    flow.fetch_token(authorization_response=authorization_response)
    
    credentials = flow.credentials
    
    # Store credentials in user profile
    profile = request.user.profile
    profile.google_calendar_refresh_token = credentials.refresh_token
    profile.google_calendar_access_token = credentials.token
    profile.google_calendar_token_expiry = credentials.expiry
    profile.save()
    
    # Clear state from session
    del request.session['google_calendar_oauth_state']
    
    messages.success(request, 'Google Calendar connected successfully!')
    return redirect('core:study_sessions_list')


def sync_session_to_google_calendar(session, profile):
    """Create a Google Calendar event for a study session."""
    creds = get_google_calendar_credentials(profile)
    if not creds:
        print(f"DEBUG: No credentials found for user {profile.user.username}")
        return None
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Ensure datetime is timezone-aware
        start_time = session.start_time
        end_time = session.end_time
        if start_time.tzinfo is None:
            from django.utils import timezone
            start_time = timezone.make_aware(start_time)
        if end_time.tzinfo is None:
            from django.utils import timezone
            end_time = timezone.make_aware(end_time)
        
        # Prepare event
        event = {
            'summary': session.title,
            'description': session.description or f'Study session at {session.location}',
            'start': {
                'dateTime': start_time.isoformat(),
                'timeZone': str(start_time.tzinfo) if start_time.tzinfo else 'UTC',
            },
            'end': {
                'dateTime': end_time.isoformat(),
                'timeZone': str(end_time.tzinfo) if end_time.tzinfo else 'UTC',
            },
            'location': session.location,
        }
        
        # Add attendees (participants)
        attendees = []
        if session.creator.email:
            attendees.append({'email': session.creator.email})
        for participant in session.participants.all():
            if participant.email:
                attendees.append({'email': participant.email})
        if attendees:
            event['attendees'] = attendees
        
        # Create event
        print(f"DEBUG: Creating calendar event: {event}")
        created_event = service.events().insert(calendarId='primary', body=event).execute()
        print(f"DEBUG: Event created successfully: {created_event.get('id')}")
        return created_event.get('id')
    
    except HttpError as error:
        print(f'ERROR: Google Calendar API error: {error}')
        print(f'ERROR: Error details: {error.error_details if hasattr(error, "error_details") else "N/A"}')
        return None
    except Exception as error:
        print(f'ERROR: Unexpected error syncing to Google Calendar: {error}')
        import traceback
        traceback.print_exc()
        return None


def update_google_calendar_event(session, profile):
    """Update an existing Google Calendar event."""
    creds = get_google_calendar_credentials(profile)
    if not creds or not session.google_calendar_event_id:
        return None
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Get existing event
        event = service.events().get(calendarId='primary', eventId=session.google_calendar_event_id).execute()
        
        # Update event
        event['summary'] = session.title
        event['description'] = session.description or f'Study session at {session.location}'
        event['start'] = {
            'dateTime': session.start_time.isoformat(),
            'timeZone': 'UTC',
        }
        event['end'] = {
            'dateTime': session.end_time.isoformat(),
            'timeZone': 'UTC',
        }
        event['location'] = session.location
        
        # Update attendees
        attendees = [{'email': session.creator.email}]
        for participant in session.participants.all():
            if participant.email:
                attendees.append({'email': participant.email})
        event['attendees'] = attendees
        
        # Update event
        updated_event = service.events().update(calendarId='primary', eventId=session.google_calendar_event_id, body=event).execute()
        return updated_event.get('id')
    
    except HttpError as error:
        print(f'An error occurred: {error}')
        return None


def delete_google_calendar_event(session, profile):
    """Delete a Google Calendar event."""
    creds = get_google_calendar_credentials(profile)
    if not creds or not session.google_calendar_event_id:
        return False
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        service.events().delete(calendarId='primary', eventId=session.google_calendar_event_id).execute()
        return True
    except HttpError as error:
        print(f'An error occurred: {error}')
        return False
