from django.contrib import admin

# Register your models here.
from .models import Action, Invoice, LineItem

admin.site.register(Action)
admin.site.register(Invoice)
admin.site.register(LineItem)