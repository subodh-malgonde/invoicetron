from django.contrib import admin

# Register your models here.
from .models import Company,Employee,Team,Customer,StripeAccountDetails

admin.site.register(Company)
admin.site.register(Customer)
admin.site.register(Employee)
admin.site.register(Team)
admin.site.register(StripeAccountDetails)