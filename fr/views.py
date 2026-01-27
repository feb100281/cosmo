from django.shortcuts import render
from django.http import HttpResponseRedirect
from django.urls import reverse

def landing_page(request):
    return render(request, 'landing.html')

def redirect_to_admin(request):
    return HttpResponseRedirect(reverse('admin:index'))