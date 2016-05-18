# -*- coding: utf-8 -*-
from rest_framework import serializers
from .models import *
from rest_framework.authtoken.models import Token
from rest_framework.validators import UniqueValidator

class AvatarSerializer(serializers.ModelSerializer):
    avatar = serializers.ImageField

    class Meta:
        model = User
        fields = ('avatar', )


class DropSerializer(serializers.ModelSerializer):
    to_user_info = serializers.SerializerMethodField()
    from_user_info = serializers.SerializerMethodField()

    class Meta:
        model = Drop
        read_only_fields = ('id', )
        fields = ('id', 'from_user', 'to_user', 'message', 'emoji', 'public', 'read_status', 'type', 'to_user_info',
                  'from_user_info', 'created_at', 'liked')

    def get_to_user_info(self, instance):
        return SimpleUserSerializer(instance.to_user).data

    def get_from_user_info(self, instance):
        return SimpleUserSerializer(instance.from_user).data


class SimpleUserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'total_friend_count', 'total_request_count', 'avatar', 'desc',
                  'public_drops', 'full_name')

    def get_avatar(self, instance):
        return instance.avatar.url if instance.avatar else ''


class DetailedUserSerializer(serializers.ModelSerializer):
    avatar = serializers.SerializerMethodField()
    friend_status = serializers.SerializerMethodField()
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'total_friend_count', 'total_request_count', 'avatar', 'desc',
                  'public_drops', 'full_name', 'friend_status', 'push_new_msg', 'push_friend_req', 'push_read_msg',
                  'push_liked_msg')

    def get_avatar(self, instance):
        return instance.avatar.url if instance.avatar else ''

    def get_friend_status(self, instance):
        view = self.context['view']
        current_user = view.request.user

        status = 'none'
        fs = Friendship.objects.filter(from_user=current_user, to_user=instance).first()
        if fs:
            if fs.approved:
                status = 'friend'
            else:
                status = 'requested'
        else:
            fs = Friendship.objects.filter(from_user=instance, to_user=current_user).first()
            if fs:
                if fs.approved:
                    status = 'friend'
                else:
                    status = 'received'
            else:
                blocked = Blockship.objects.filter(from_user=current_user, to_user=instance).first()
                if blocked:
                    status = 'blocked'
                else:
                    blocked = Blockship.objects.filter(from_user=instance, to_user=current_user).first()
                    if blocked:
                        status = 'blockedby'
        return status


class RecentUserSerializer(serializers.BaseSerializer):
    def to_representation(self, obj):
        u = User.objects.get(pk=obj['id'])
        return SimpleUserSerializer(u).data


class PushSerializer(serializers.Serializer):
    msg = serializers.CharField(max_length=200)


class DummyUserSerializer(serializers.Serializer):
    username = serializers.CharField(max_length=200)
    password = serializers.CharField(max_length=200)


class PasswordSerializer(serializers.Serializer):
    password = serializers.CharField(max_length=200)

    def save(self, **kwargs):
        request = self.context.get("request")
        if request and hasattr(request, "user"):
            password = self.validated_data['password']
            request.user.set_password(password)
            request.user.save()


class UserSerializer(serializers.ModelSerializer):
    username = serializers.CharField(max_length=255, error_messages={'required': 'Hey! All fields are required.'},
                                     validators=[UniqueValidator(queryset=User.objects.all(),
                                                                 message='Sorry! That username is taken.')])
    email = serializers.CharField(max_length=255, error_messages={'required': 'Hey! All fields are required.'},
                                  validators=[UniqueValidator(queryset=User.objects.all(),
                                                              message='Hey! That email has already been registered.')])
    avatar = serializers.SerializerMethodField()
    password = serializers.CharField(required=False, write_only=True)
    token = serializers.SerializerMethodField()

    class Meta:
        model = User
        read_only_fields = ('total_friend_count', 'total_request_count', 'avatar')
        fields = ('id', 'email', 'username', 'total_friend_count', 'total_request_count', 'avatar', 'desc', 'password',
                  'public_drops', 'token', 'full_name', 'push_new_msg', 'push_friend_req', 'push_read_msg',
                  'push_liked_msg')



    def get_token(self, obj):
        token, created = Token.objects.get_or_create(user=obj)
        return token.key

    def get_avatar(self, instance):
        return instance.avatar.url if instance.avatar else ''

    def create(self, validated_data):
        if validated_data.get('password'):
            user = User()
            user.set_password(validated_data['password'])
            validated_data['password'] = user.password
        else:
            raise serializers.ValidationError('Hey! All fields are required.')

        return super(UserSerializer, self).create(validated_data)

    """
    def update(self, instance, validated_data):

        if validated_data.get('password', False):
            user = User()
            user.set_password(validated_data['password'])
            validated_data['password'] = user.password

        return super(UserSerializer, self).update(instance, validated_data)
    """