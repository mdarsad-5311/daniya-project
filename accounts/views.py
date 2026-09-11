from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import resolve_url
from django.utils.http import url_has_allowed_host_and_scheme
from orders.models import Order


def register_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Welcome! Your account has been created.')
            return redirect(_get_safe_next_url(request))
    else:
        form = UserCreationForm()
    return render(request, 'accounts/register.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def login_view(request):
    if request.user.is_authenticated:
        return redirect('home')
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f'Welcome back, {user.first_name or user.username}!')
            return redirect(_get_safe_next_url(request))
    else:
        form = AuthenticationForm()
    return render(request, 'accounts/login.html', {
        'form': form,
        'next': request.GET.get('next', ''),
    })


def _get_safe_next_url(request):
    next_url = request.POST.get('next') or request.GET.get('next')
    if next_url and url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return next_url
    return resolve_url(settings.LOGIN_REDIRECT_URL)


def logout_view(request):
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'You have been signed out.')
    return redirect('home')


@login_required
def profile_view(request):
    orders = (
        Order.objects
        .filter(user=request.user)
        .prefetch_related('items', 'items__product')
        .order_by('-created_at')
    )
    return render(request, 'accounts/profile.html', {'orders': orders})

from .models import NewsletterSubscriber

def subscribe_newsletter(request):
    if request.method == 'POST':
        email = request.POST.get('email')
        if email:
            NewsletterSubscriber.objects.get_or_create(email=email)
            return HttpResponse('<div class="rounded-lg bg-primary px-4 py-2 text-sm font-medium text-primary-foreground shadow flex items-center justify-center gap-1.5 h-11"><i data-lucide="check" class="h-4 w-4"></i> Thanks for subscribing!</div>')
    return HttpResponse('Invalid request')
