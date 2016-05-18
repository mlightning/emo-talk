# -*- coding: utf-8 -*-
from django.conf.urls import patterns, url, include
from rest_framework import routers
from .views import *
from rest_framework.authtoken import views
from django.conf import settings

urlpatterns = patterns(
    '',
    url(r'^login/', LoginApiView.as_view(), name='login'),
    url(r'^signup/', UserCreateView.as_view(), name='new-user'),
    url(r'^current_user/friend_request/(?P<user_id>[0-9]+)$', FriendRequestView.as_view(), name='user-friend-request'),
    url(r'^current_user/friend_approve/(?P<user_id>[0-9]+)$', FriendApproveView.as_view(), name='user-friend-approve'),
    url(r'^current_user/block/(?P<user_id>[0-9]+)$', BlockUserView.as_view(), name='block-user'),
    url(r'^current_user/friend_decline/(?P<user_id>[0-9]+)$', FriendDeclineView.as_view(), name='user-friend-decline'),
    url(r'^current_user/avatar$', AvatarUpdateView.as_view(), name='user-avatar'),
    url(r'^current_user/recent_senders', RecentSenderView.as_view()),
    url(r'^current_user/register_device', DeviceTokenRegisterView.as_view()),
    url(r'^current_user/change_password', ChangePasswordAPIView.as_view()),
    url(r'^current_user/drops/clean', CleanDropView.as_view()),
    url(r'^current_user/$', UserDetail.as_view(), name='user'),
    url(r'^users/$', UserListView.as_view(), name='users-list'),

    url(r'^users/(?P<pk>[0-9]+)/$', UserDetailView.as_view(), name='user-detail'),
    url(r'^users/(?P<user_id>[0-9]+)/friends', FriendsView.as_view(), name='friends-list'),
    url(r'^users/(?P<user_id>[0-9]+)/requests', RequestsView.as_view(), name='requests-list'),
    url(r'^api-auth/', include('rest_framework.urls',
                               namespace='rest_framework')),
    url(r'^media/(?P<path>.*)$', 'django.views.static.serve', {
        'document_root': settings.MEDIA_ROOT}),

    url(r'^drops/(?P<pk>.*)/$', DropUpdateDetailView.as_view(), name='drop-update'),
    url(r'^drops$', DropApiView.as_view()),

    url(r'^forget_password/(?P<username>.*)$', ForgetPassword.as_view(), name='forget-password'),
    url(r'^reset_password/(?P<token>.*)/$', reset_password, name='reset-password'),
    url(r'^reset_badge/$', ResetBadgeView.as_view(), name='reset-badge'),

    url(r'^test_push/$', TestPushView.as_view(), name='test-push')
)