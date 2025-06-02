from mongoengine import (
    Document, StringField, EmailField, ListField, ReferenceField, 
    DateTimeField, IntField, CASCADE
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime


class User(Document):
    email = EmailField(required=True, unique=True)
    username = StringField(required=True, unique=True)
    password_hash = StringField(required=True)
    profile_image = StringField(default="default_profile.png")  # filename or URL
    joined_subspheres = ListField(ReferenceField('Subsphere'))

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    meta = {
        'indexes': [
            'email',
            'username',
        ]
    }


class Subsphere(Document):
    name = StringField(required=True, unique=True)
    description = StringField()
    created_at = DateTimeField(default=datetime.utcnow)
    created_by = ReferenceField(User, reverse_delete_rule=CASCADE)
    members = ListField(ReferenceField(User))

    meta = {
        'indexes': [
            'name',
            'created_by',
        ]
    }


class Post(Document):
    title = StringField(required=True)
    content = StringField()
    image = StringField()  # filename or URL
    created_at = DateTimeField(default=datetime.utcnow)
    created_by = ReferenceField(User, reverse_delete_rule=CASCADE)
    subsphere = ReferenceField(Subsphere, reverse_delete_rule=CASCADE)
    upvotes = IntField(default=0)
    downvotes = IntField(default=0)

    meta = {
        'indexes': [
            'created_by',
            'subsphere',
            'created_at',
        ]
    }


class Comment(Document):
    content = StringField(required=True)
    created_at = DateTimeField(default=datetime.utcnow)
    created_by = ReferenceField(User, reverse_delete_rule=CASCADE)
    post = ReferenceField(Post, reverse_delete_rule=CASCADE)
    parent_comment = ReferenceField('self', null=True, required=False)
    upvotes = IntField(default=0)
    downvotes = IntField(default=0)

    meta = {
        'indexes': [
            'post',
            'created_by',
            'parent_comment',
            'created_at',
        ]
    }


class Vote(Document):
    VOTE_TYPES = ('upvote', 'downvote')
    user = ReferenceField(User, reverse_delete_rule=CASCADE, required=True)
    post = ReferenceField(Post, null=True, required=False, reverse_delete_rule=CASCADE)
    comment = ReferenceField(Comment, null=True, required=False, reverse_delete_rule=CASCADE)
    vote_type = StringField(choices=VOTE_TYPES, required=True)
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'indexes': [
            'user',
            'post',
            'comment',
        ]
    }
