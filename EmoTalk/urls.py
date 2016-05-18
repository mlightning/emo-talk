from django.conf.urls import patterns, include, url
urlpatterns = patterns(
    '',
    url(r'^docs/', include('rest_framework_docs.urls')),
    url(r'^api/', include('api.urls', namespace='api')),
)
