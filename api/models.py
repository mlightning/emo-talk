# -*- coding: utf-8 -*-
from django.contrib.auth.models import AbstractUser
from PIL import Image
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from rest_framework.authtoken.models import Token
from push_notifications.models import APNSDevice
from push_notifications.apns import apns_send_message, apns_send_bulk_message
from django.conf import settings
import uuid, emoji

DROP_TYPE = (
	('text', 'Text'),
	('photo', 'Photo'),
	('video', 'Video'),
)


class DropDeviceManager(models.Manager):
	def get_queryset(self):
		return DropDeviceQuerySet(self.model)


class DropDeviceQuerySet(models.query.QuerySet):
	def send_message(self, message, increase_badge=False, **kwargs):
		if self:
			for d in self.all():
				d.send_message(message, increase_badge, **kwargs)


class DropDevice(APNSDevice):
	badge = models.IntegerField(default=0)

	objects = DropDeviceManager()

	def send_message(self, message, increase_badge=False, **kwargs):
		if increase_badge:
			self.badge = self.badge + 1
			self.save()

		kwargs['badge'] = self.badge
		return apns_send_message(registration_id=self.registration_id, alert=message, **kwargs)


def upload_to(instance, filename):
	ext = filename.split('.')[-1]
	filename = "%s.%s" % (uuid.uuid4(), ext)
	return 'avatars/{}/{}'.format(instance.id, filename)


def send_push(u, msg, increase_badge, extra):
	devices = DropDevice.objects.filter(user=u)
	devices.send_message(msg, increase_badge, extra=extra)


class User(AbstractUser):
	public_drops = models.BooleanField(default=True)
	full_name = models.CharField(max_length=255, default='', null=True, blank=True)
	total_friend_count = models.IntegerField(default=0)
	total_request_count = models.IntegerField(default=0)
	avatar = models.ImageField(blank=True, null=True, upload_to=upload_to, editable=True, default='')
	desc = models.CharField(max_length=255, default='', null=True, blank=True)
	friendships = models.ManyToManyField('self', through='Friendship', symmetrical=False, related_name='related_to')
	blockships = models.ManyToManyField('self', through='Blockship', symmetrical=False, related_name='blocked')
	push_new_msg = models.BooleanField(default=True)
	push_friend_req = models.BooleanField(default=True)
	push_read_msg = models.BooleanField(default=True)
	push_liked_msg = models.BooleanField(default=True)

	def _update_friendship_metric(self, user):
		user.total_friend_count = Friendship.objects.filter(to_user=user, approved=True).count()
		user.total_request_count = Friendship.objects.filter(to_user=user, approved=False).count()

		user.save()

	def request_friendship(self, user):
		approved = False
		opposite = Friendship.objects.filter(from_user=user, to_user=self).first()
		if opposite:
			opposite.approved = True
			opposite.save()
			approved = True
			if user.push_friend_req:
				send_push(user, '@%s accepted your friendship request' % self.username, False,
						{'type': 'friend_ship_accepted', 'from_user_id': user.id, 'to_user_id': self.id})
			self._update_friendship_metric(self)

		friendship, created = Friendship.objects.get_or_create(from_user=self, to_user=user, approved=approved)
		if not approved:
			if user.push_friend_req:
				send_push(user, '@%s wants to be your friend!' % self.username, False,
						{'type': 'friend_ship_request', 'from_user_id': self.id, 'to_user_id': user.id})
		self._update_friendship_metric(user)

		return friendship

	def approve_friendship(self, user):
		friendship, created = Friendship.objects.get_or_create(from_user=user, to_user=self)
		friendship.approved = True
		friendship.save()
		friendship, created = Friendship.objects.get_or_create(from_user=self, to_user=user)
		friendship.approved = True
		friendship.save()
		if user.push_friend_req:
			send_push(user, '@%s accepted your friendship request' % self.username, False,
						{'type': 'friend_ship_accepted', 'from_user_id': user.id, 'to_user_id': self.id})

		self._update_friendship_metric(user)
		self._update_friendship_metric(self)

		return friendship

	def decline_friendship(self, user):
		Friendship.objects.filter(from_user=user, to_user=self).delete()
		msg = '@%s declined your friendship request' % self.username
		if user.push_friend_req:
			send_push(user, msg, False, {'type': 'friend_ship_declined', 'from_user_id': user.id, 'to_user_id': self.id})
		self._update_friendship_metric(self)

	def cancel_request(self, user):
		Friendship.objects.filter(from_user=self, to_user=user).delete()
		msg = '@%s canceled friendship request' % self.username
		if user.push_friend_req:
			send_push(user, msg, False, {'type': 'friend_ship_cancel', 'from_user_id': self.id, 'to_user_id': user.id})
		self._update_friendship_metric(self)

	def delete_friend(self, user):
		Friendship.objects.filter(from_user=user, to_user=self).delete()
		Friendship.objects.filter(from_user=self, to_user=user).delete()
		msg = '@%s removed you from friends' % self.username
		if user.push_friend_req:
			send_push(user, msg, False, {'type': 'friend_ship_delete', 'from_user_id': self.id, 'to_user_id': user.id})
		self._update_friendship_metric(self)
		self._update_friendship_metric(user)

	def block_user(self, user):
		blockship, created = Blockship.objects.get_or_create(from_user=self, to_user=user)
		Friendship.objects.filter(from_user=user, to_user=self).delete()
		Friendship.objects.filter(from_user=self, to_user=user).delete()
		if user.push_friend_req:
			send_push(user, '@%s blocked you' % self.username, False, {'type': 'block_user', 'from_user_id': self.id})
		return blockship

	def unblock_user(self, user):
		Blockship.objects.filter(from_user=self, to_user=user).delete()
		if user.push_friend_req:
			send_push(user, '@%s unblocked you' % self.username, False, {'type': 'unblock_user', 'from_user_id': self.id})



class Friendship(models.Model):
	from_user = models.ForeignKey(User, related_name='from_user')
	to_user = models.ForeignKey(User, related_name='to_user')
	approved = models.BooleanField(default=False)


class Blockship(models.Model):
	from_user = models.ForeignKey(User, related_name='blocked_from_user')
	to_user = models.ForeignKey(User, related_name='blocked_to_user')


class Drop(models.Model):
	from_user = models.ForeignKey(User, related_name='message_from_user')
	to_user = models.ForeignKey(User, related_name='message_to_user')
	emoji = models.IntegerField(blank=False, null=False, default=0)
	message = models.TextField(blank=False, default=0, null=False)
	public = models.BooleanField(default=False)
	liked = models.BooleanField(default=False)
	read_status = models.BooleanField(default=False)
	type = models.CharField(max_length=7, choices=DROP_TYPE)
	from_user_cleaned = models.BooleanField(default=False)
	to_user_cleaned = models.BooleanField(default=False)
	created_at = models.DateTimeField(null=True, auto_now=True)

	class Meta:
		ordering = ['-id']


class UserCode(models.Model):
	user = models.ForeignKey(User)
	code = models.CharField(max_length=40, primary_key=True, default='')
	created_at = models.DateTimeField(auto_now_add=True)

@receiver(post_save, sender=User)
def create_auth_token(sender, instance=None, created=False, **kwargs):
	if created:
		Token.objects.create(user=instance)


@receiver(post_save, sender=Drop)
def drop_updated(sender, instance=None, created=False, **kwargs):
	if created:
		if instance.to_user.push_new_msg:
			devices = DropDevice.objects.filter(user=instance.to_user)
			msg = '@%s sent you a %s drop' % (instance.from_user.username, settings.DROP_EMOJI[instance.emoji])
			msg = emoji.emojize(msg, use_aliases=True)
			devices.send_message(msg, True, extra={'type': 'drop', 'id': instance.id})
