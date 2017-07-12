from django.conf.urls import url
from .import views

urlpatterns = [
    url(r'^$', views.index, name='index'),
    url(r'^slack/invoicetron/$', views.slack_hook, name='slack_hook'),
    url(r'^invoice/(?P<invoice_id>[0-9]+)+/$', views.generate_invoice, name='generate_pdf'),
    url(r'^connected/$', views.stripe_oauth, name='connect_with_stripe'),
    # url(r'^invoicetron/$', views.index, name='Add New Team'),
    url(r'^slack/oauth/$', views.slack_oauth, name='Slack Oauth')
]



