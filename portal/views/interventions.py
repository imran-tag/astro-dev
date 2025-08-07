# technician/portal/views/interventions.py

from django.shortcuts import render
from django.views import View
from django.contrib import messages


class InterventionListView(View):
    template_name = 'portal/interventions/list.html'

    def get(self, request):
        return render(request, self.template_name, {'interventions': []})