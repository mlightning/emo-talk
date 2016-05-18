# -*- coding: utf-8 -*-
from .serializers import *
from .models import *
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework import status
from PIL import Image
from rest_framework import generics
from rest_framework.pagination import PageNumberPagination
from rest_framework.views import APIView
from django.http import Http404
from rest_framework import filters
from django.db.models import Q, Count
from django.core.mail.message import EmailMultiAlternatives
import random, string
from django.template.loader import get_template
from django.template import Context
from django.core.urlresolvers import reverse
from django.shortcuts import render
from django.conf import settings
import emoji


class StandardResultsSetPagination(PageNumberPagination):
	page_size = 30
	page_size_query_param = 'page_size'
	max_page_size = 1000


class FriendsView(generics.ListAPIView):
	serializer_class = UserSerializer
	permission_classes = (permissions.IsAuthenticated, )
	pagination_class = StandardResultsSetPagination

	def list(self, request, *args, **kwargs):
		user_id = kwargs.get('user_id')
		u = User.objects.get(pk=user_id)
		queryset = u.related_to.filter(from_user__approved=True)
		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)

		serializer = self.get_serializer(queryset, many=True)
		return Response(serializer.data)


class RequestsView(generics.ListAPIView, generics.DestroyAPIView):
	serializer_class = UserSerializer
	permission_classes = (permissions.IsAuthenticated, )
	pagination_class = StandardResultsSetPagination

	def list(self, request, *args, **kwargs):
		user_id = kwargs.get('user_id')
		u = User.objects.get(pk=user_id)
		queryset = u.related_to.filter(from_user__approved=False)
		page = self.paginate_queryset(queryset)
		if page is not None:
			serializer = self.get_serializer(page, many=True)
			return self.get_paginated_response(serializer.data)

		serializer = self.get_serializer(queryset, many=True)
		return Response(serializer.data)


class UserDetail(APIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = UserSerializer

	def get_object(self, request):
		pk = request.user.pk
		try:
			return User.objects.get(pk=pk)
		except User.DoesNotExist:
			raise Http404

	def get(self, request):
		user = self.get_object(request)
		serializer = UserSerializer(user)
		return Response(serializer.data)

	def put(self, request):
		user = self.get_object(request)
		serializer = UserSerializer(user, data=request.data, partial=True)
		if serializer.is_valid():
			serializer.save()
			return Response(serializer.data)
		return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

	"""
	def delete(self, request):
		user = self.get_object(request)
		user.delete()
		return Response(status=status.HTTP_204_NO_CONTENT)
	"""


class FriendRequestView(generics.RetrieveDestroyAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			try:
				self.request.user.request_friendship(friend)
			except Exception, e:
				return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response("user_id is required", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)

	def delete(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			self.request.user.cancel_request(friend)
		else:
			return Response("Invalid User", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class FriendApproveView(generics.RetrieveDestroyAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			try:
				self.request.user.approve_friendship(friend)
			except Exception, e:
				return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response("user_id is required", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)

	def delete(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			self.request.user.delete_friend(friend)
		else:
			return Response("Invalid User", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class FriendDeclineView(generics.RetrieveAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			try:
				self.request.user.decline_friendship(friend)
			except Exception, e:
				return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response("user_id is required", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)


class UserListView(generics.ListAPIView):
	serializer_class = SimpleUserSerializer
	pagination_class = StandardResultsSetPagination
	filter_backends = (filters.SearchFilter,)
	search_fields = ('username', 'email', 'full_name', )

	def get_queryset(self):
		u = self.request.user
		return User.objects.exclude(pk=u.pk)


class UserDetailView(generics.RetrieveAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = DetailedUserSerializer
	queryset = User.objects.all()


class UserCreateView(generics.CreateAPIView):
	serializer_class = UserSerializer


class AvatarUpdateView(generics.CreateAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = AvatarSerializer

	def post(self, request, *args, **kwargs):
		if 'avatar' in request.data:
			u = request.user
			if u.avatar:
				u.avatar.delete()
			upload = request.data['avatar']
			u.avatar.save(upload.name, upload)

			image = Image.open(upload)
			(width, height) = image.size
			if width > 240 and height > 240:
				size = (240, 240)
				image = image.resize(size, Image.ANTIALIAS)
				print u.avatar.path
				image.save(u.avatar.path)

			return Response(UserSerializer(u).data, status=status.HTTP_201_CREATED)

		else:
			return Response(status=status.HTTP_400_BAD_REQUEST)


class DropUpdateDetailView(generics.UpdateAPIView, generics.RetrieveAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	queryset = Drop.objects.all()
	serializer_class = DropSerializer
	model = Drop

	def patch(self, request, *args, **kwargs):
		instance = self.get_object()
		liked = request.data.get('liked')
		read_status = request.data.get('read_status')


		if liked and instance.from_user.push_liked_msg and not instance.from_user_cleaned:
			devices = DropDevice.objects.filter(user=instance.from_user)
			msg = emoji.emojize('@%s liked your %s drop' %
			                        (instance.to_user.username, settings.DROP_EMOJI[instance.emoji]), use_aliases=True)
			devices.send_message(msg, False, extra={'type': 'liked', 'id': instance.id})

		if read_status and instance.to_user.push_read_msg and not instance.from_user_cleaned:
			msg = emoji.emojize('@%s read your %s drop' %
			                        (instance.to_user.username, settings.DROP_EMOJI[instance.emoji]), use_aliases=True)
			devices = DropDevice.objects.filter(user=instance.from_user)
			devices.send_message(msg, False, extra={'type': 'read', 'id': instance.id})

		return self.partial_update(request, *args, **kwargs)


class DropApiView(generics.ListCreateAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = DropSerializer
	pagination_class = StandardResultsSetPagination

	def get_queryset(self):
		public = self.request.query_params.get('public', False)
		if public:
			public = public == 'Y'
		return Drop.objects.filter((Q(to_user=self.request.user) & Q(to_user_cleaned=False)) |
		                           (Q(from_user=self.request.user) & Q(from_user_cleaned=False)), public=public)

	def get_serializer(self, *args, **kwargs):
		if "data" in kwargs:
			data = kwargs["data"]

			if isinstance(data, list):
				kwargs["many"] = True

		return super(DropApiView, self).get_serializer(*args, **kwargs)


class CleanDropView(generics.ListAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, request, *args, **kwargs):
		user = request.user
		public = request.query_params.get('public') == 'Y'
		read_only = request.query_params.get('delete_read_only') == 'Y'
		drops = Drop.objects.filter(to_user=user, public=public, to_user_cleaned=False)
		if read_only:
			drops = drops.filter(read_status=True)
		drops.update(to_user_cleaned=True)

		drops = Drop.objects.filter(from_user=user, public=public, from_user_cleaned=False)
		if read_only:
			drops = drops.filter(read_status=True)
		drops.update(from_user_cleaned=True)

		Drop.objects.filter(to_user_cleaned=True, from_user_cleaned=True).delete()

		view = DropApiView.as_view()
		return view(request, *args, **kwargs)


class RecentSenderView(generics.ListAPIView):
	serializer_class = SimpleUserSerializer
	permission_classes = (permissions.IsAuthenticated, )

	def get_queryset(self):
		public = self.request.query_params.get('public', False)
		if public == 'Y':
			query_set = User.objects.raw(
				'SELECT distinct to_user_id as id from api_drop where from_user_id=%s order by created_at desc limit 15' % self.request.user.id)
		else:
			query_set = User.objects.raw("SELECT distinct f.to_user_id as id from api_drop d " +
			                             "join api_friendship f on d.from_user_id=f.from_user_id and d.to_user_id and f.to_user_id and approved=1 " +
			                             "where d.from_user_id=%s order by created_at desc limit 15" % self.request.user.id)
		return query_set


class DeviceTokenRegisterView(generics.ListAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, request, *args, **kwargs):
		u = request.user
		registration_id = request.query_params.get('token')
		device, created = DropDevice.objects.get_or_create(registration_id=registration_id)
		device.user = u
		device.save()

		return Response({'status': 'ok'})


class ResetBadgeView(generics.ListAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def get(self, request, *args, **kwargs):
		token = request.query_params.get('token')
		DropDevice.objects.filter(registration_id=token).all().update(badge=0)

		return Response({'status': 'ok'})


class LoginApiView(generics.CreateAPIView):
	serializer_class = DummyUserSerializer

	def post(self, request, *args, **kwargs):
		username = request.data.get('username')
		password = request.data.get('password')
		token = request.data.get('token')

		user = User.objects.filter(username=username).first()
		if user:
			if user.check_password(password):
				if token:
					device, created = DropDevice.objects.get_or_create(registration_id=token)
					device.user = user
					device.save()
				return Response(UserSerializer(user).data)
			else:
				return Response({'error': 'You entered the wrong username/password.'}, status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response({'error': 'You entered the wrong username/password.'}, status=status.HTTP_400_BAD_REQUEST)


class BlockUserView(generics.CreateAPIView, generics.DestroyAPIView):
	permission_classes = (permissions.IsAuthenticated, )

	def post(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			try:
				self.request.user.block_user(friend)
			except Exception, e:
				return Response(str(e), status=status.HTTP_400_BAD_REQUEST)
		else:
			return Response("user_id is required", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_201_CREATED)

	def delete(self, *args, **kwargs):
		user_id = kwargs.get('user_id')
		friend = User.objects.get(pk=user_id)
		if friend:
			self.request.user.unblock_user(friend)
		else:
			return Response("Invalid User", status=status.HTTP_400_BAD_REQUEST)

		return Response({'status': 'ok'}, status=status.HTTP_200_OK)


class ChangePasswordAPIView(generics.CreateAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = PasswordSerializer


class ForgetPassword(generics.ListAPIView):
	def get(self, request, *args, **kwargs):
		username = kwargs.get('username')
		if not username:
			return Response({'status': 'error', 'msg': 'Username is required'}, status=status.HTTP_400_BAD_REQUEST)
		user = User.objects.filter(username=username).first()
		if not user:
			return Response({'status': 'error', 'msg': 'User not found'}, status=status.HTTP_400_BAD_REQUEST)
		code = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(15))
		user_code = UserCode(user=user, code=code)
		user_code.save()

		d = {'url': request.build_absolute_uri(reverse('api:reset-password', kwargs={'token': code}))}
		plaintext = get_template('pw_reset.txt')
		htmly = get_template('pw_reset.html')
		subject, from_email, to = '[EmoTalk] Password Reset', 'support@crowdpostapp.com', user.email
		text_content = plaintext.render(d)
		html_content = htmly.render(d)
		msg = EmailMultiAlternatives(subject, text_content, from_email, [to])
		msg.attach_alternative(html_content, "text/html")
		msg.send()

		return Response({'status': 'ok'})


class TestPushView(generics.CreateAPIView):
	permission_classes = (permissions.IsAuthenticated, )
	serializer_class = PushSerializer

	def post(self, request, *args, **kwargs):
		msg = emoji.emojize(request.data.get('msg'), use_aliases=True)
		users = DropDevice.objects.filter(user=request.user).all()
		users.send_message(msg, False)

		return Response({'status': 'ok'})


def reset_password(request, token):
	user_code = UserCode.objects.filter(pk=token).first()
	if user_code:
		user = user_code.user
		user.email_verified = True
		user.save()
		if request.POST and request.POST['new_password']:
			if request.POST['new_password'] == request.POST['confirm_password']:
				if len(request.POST['new_password']) > 3:
					user.set_password(request.POST['new_password'])
					user.save()
					user_code.delete()

					return render(request, 'reset_password.html', {'user': user, 'token': token, 'success': True})
				else:
					return render(request, 'reset_password.html', {'user': user, 'token': token, 'error': True,
					                                               'msg': 'Password should be at least 4 characters long.'})
			else:
				return render(request, 'reset_password.html', {'user': user, 'token': token, 'error': True,
				                                               'msg': 'Please match passwords!'})

		return render(request, 'reset_password.html', {'user': user, 'token': token})
	else:
		return render(request, 'reset_password.html', {'user': False})


