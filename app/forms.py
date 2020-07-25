from flask_wtf import FlaskForm
from wtforms import (StringField, PasswordField,
                     BooleanField, SubmitField,
                     TextAreaField)
from wtforms.validators import (ValidationError, DataRequired,
                                Email, EqualTo, Length)
from app.models import User, Watchlist, DataBase


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember_me = BooleanField('Remember Me', default=False)
    submit = SubmitField('Sign In')


class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired(),
                             EqualTo('confirm',
                             message='Passwords must match')])
    confirm = PasswordField('Repeat Password')
    submit = SubmitField('Register')

    def validate_username(self, username):
        user = User()
        ok = user.validate_name(username.data)
        if not ok:
            raise ValidationError('Please use a different username.')

    def validate_email(self, email):
        user = User()
        ok = user.validate_email(email.data)
        if not ok:
            raise ValidationError('Please use a different email address.')


class ReviewForm(FlaskForm):
    review = TextAreaField('Your opinion', validators=[DataRequired()])
    submit = SubmitField('Submit')


class WatchlistForm(FlaskForm):
    title = StringField("Title", validators=[DataRequired(), Length(max=12)])
    content = TextAreaField("Content")
    submit = SubmitField("Send")

    def __init__(self, username):
        self.username = username
        super().__init__()

    def validate_title(self, title):
        watchlist = Watchlist()
        ok = watchlist.validate_listname(self.username, title.data)
        if not ok:
            raise ValidationError('Please use a different title.')


class UpdateList(WatchlistForm):
    def __init__(self, username, list_name):
        self.list_name = list_name
        super().__init__(username)

    def validate_title(self, title):
        watchlist = Watchlist()
        if title.data != self.list_name:
            ok = watchlist.validate_listname(self.username, title.data)
            if not ok:
                raise ValidationError('Please use a different title.')
