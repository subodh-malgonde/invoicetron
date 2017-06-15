from django.conf.urls import url
from .import views

urlpatterns = [
    url(r'^$', views.post_list, name='post_list'),
    url(r'^slack/invoicetron/$', views.slack_hook, name='slack_hook')
]
