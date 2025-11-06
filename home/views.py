from django.shortcuts import render, redirect


# Create your views here.
def index(request):
    if request.user.is_authenticated:
        # Assuming you have a 'profile' or 'dashboard' url name
        return redirect("accounts:profile")  # Or wherever you want logged-in users to go
    return render(request, "home/index.html")
