from django.conf.urls import url
from .import views

urlpatterns = [
    url(r'^$', views.post_list, name='post_list'),
    url(r'^slack/invoicetron/$', views.slack_hook, name='slack_hook'),
    url(r'^invoice/(?P<invoice_id>[0-9]+)+/$', views.generate_pdf, name='generate_pdf')
]
