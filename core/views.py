from django.shortcuts import render
from django.contrib.auth.decorators import login_required

# Create your views here.
@login_required
def swipe(request):
    # This will be the main page for logged-in users to find matches.
    return render(request, "core/swipe.html")
