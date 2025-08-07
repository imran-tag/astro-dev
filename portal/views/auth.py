# technician/portal/views/auth.py

from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages


class LoginView(View):
    template_name = 'portal/login.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        return render(request, self.template_name)