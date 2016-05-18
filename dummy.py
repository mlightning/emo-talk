#!/usr/bin/env python
import os
import sys, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "EmoTalk.settings")
django.setup()
from random import sample, choice
from api.models import User

if __name__ == "__main__":
	ids = []
	for i in range(150):
		name = 'user%s' % i
		email = '%s@test.com' % name
		pwd = 'password%s' % i
		print 'create user: %s' % name
		user, created = User.objects.get_or_create(username=name, email=email)
		if created:
			user.set_password(pwd)
			user.save()
		ids.append(user.id)

	for id in ids:
		u = User.objects.get(pk=id)
		friends = sample(ids, 15)
		print 'make friendship of %s' % u.username
		for f_id in friends:
			if id != f_id:
				f = User.objects.get(pk=f_id)
				u.request_friendship(f, choice([True, False]))
