import sqlite3
import hashlib
from flask import (render_template, g, request,
                   redirect, url_for, session,
                   flash)
from app import app
from app.forms import (LoginForm, RegisterForm,
                       ReviewForm, WatchlistForm,
                       UpdateList)
from app.models import (DataBase, Film, User,
                        login_required, Search, Person,
                        Favorites, Watchlater, Watchlist,
                        logout_required)
from datetime import timedelta
from math import ceil


@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html', title='Home')


@app.route('/top')
def top_rated():
    db = Film()
    films = db.get_top_movies()
    return render_template('top.html', films=films)


@app.route('/highest-grossing')
def boxoffice():
    db = Film()
    films = db.highest_grossing_movies()
    return render_template('boxoffice.html', films=films)


@app.route('/popular')
def popular():
    db = Film()
    films = db.get_popular_movies()
    return render_template('popular.html', films=films)


@app.route('/movie/<film_id>')
def movie(film_id):
    form = ReviewForm()
    db = Film()
    db_w = Watchlist()
    db_user = User()
    page = request.args.get('page', '1')
    if not db.check_film(film_id):
        return render_template('404.html')
    (film, directors, actors, genres,
     reviews, page, pageCount) = db.get_film(film_id, page)
    if session.get("__auth"):
        list_names = db_w.watchlist_names(session["__auth"])
        rate = db_user.check_rate(film_id)
    else:
        list_names = []
        rate = 0
    return render_template('movie.html', form=form, film=film,
                           directors=directors, actors=actors,
                           genres=genres, reviews=reviews,
                           list_names=list_names, rate=rate,
                           page=page, pageCount=pageCount)


@app.route('/movie/<film_id>', methods=['POST'])
@login_required
def write_review(film_id):
    form = ReviewForm()
    if not form.validate_on_submit():
        return redirect(url_for('movie', film_id=film_id))
    film = Film()
    user = User()
    body = form.review.data
    user_id = user.current_user(session['__auth'])
    film.write_review(body=body, user_id=user_id, film_id=film_id)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/register')
@logout_required
def register_get():
    form = RegisterForm()
    return render_template("register.html", form=form)


@app.route('/register', methods=['POST'])
def register_post():
    form = RegisterForm()
    if form.validate_on_submit():
        user = User()
        user.insert_user(name=form.username.data,
                         email=form.email.data,
                         password=form.password.data)
        return redirect(url_for('login_get'))
    return render_template('register.html', form=form)


@app.route('/login')
def login_get():
    form = LoginForm()
    return render_template('login.html', title='Sign In', form=form)


@app.route('/login', methods=['POST'])
def login_post():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        user = User().check_user(name=username,
                                 password=password)
        if user:
            if form.remember_me.data:
                session.permanent = True
                session['__auth'] = username
            else:
                session.permanent = False
                session['__auth'] = username
            return redirect('/index')
        flash('Incorect Username or Password')
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout')
@login_required
def logout():
    del session['__auth']
    return redirect('/index')


@app.route('/<username>/profile')
@login_required
def profile(username):
    page = request.args.get('page', '1')
    user = User()
    id = user.current_user(username)
    if not id:
        return render_template('404.html')
    followers = user.followers(username)
    followings = user.followings(username)
    is_following = user.is_following(username)
    reviews, page, pageCount = user.get_reviews(id, page)
    return render_template('profile.html', username=username,
                           followings=followings, followers=followers,
                           reviews=reviews, page=page,
                           pageCount=pageCount, is_following=is_following)


@app.route('/follow/<username>')
@login_required
def follow(username):
    user = User()
    if not user.current_user(username):
        return redirect('/index')
    user.follow(username)
    return redirect(url_for('profile', username=username))


@app.route('/unfollow/<username>')
@login_required
def unfollow(username):
    user = User()
    if not user.current_user(username):
        return redirect('/index')
    user.unfollow(username)
    return redirect(url_for('profile', username=username))


@app.route('/search')
def search():
    types = ('film', 'person', 'user')
    page = request.args.get('page', '1')
    title = request.args.get('query', '')
    srch_type = request.args.get('type', 'film')
    if srch_type not in types:
        srch_type = 'film'
    search = Search()
    if srch_type == 'film':
        films, page, lenght = search.search_film(title, page)
        pages = ceil(lenght/app.config['ITEMS_PER_PAGE'])
        return render_template('srch_film.html', films=films, pageCount=pages,
                               p=page, q=title, lenght=lenght)
    elif srch_type == 'person':
        persons, page, lenght = search.search_person(title, page, [1, 2])
        pages = ceil(lenght/app.config['ITEMS_PER_PAGE'])
        return render_template('srch_per.html', persons=persons,
                               pageCount=pages, p=page, q=title, lenght=lenght)
    else:
        users = search.search__user(title)
        return render_template('srch_user.html', users=users, q=title)


@app.route('/person/<person_id>')
def persons(person_id):
    db = Person()
    if person_id.isdigit() and db.check_person(person_id):
        person, as_actor, as_director, jobs = db.person_info(person_id)
        return render_template('person.html', person=person, as_actor=as_actor,
                               as_director=as_director, jobs=jobs)
    else:
        return render_template('404.html')


@app.route('/watchlater')
@login_required
def watch_later_list():
    db = Watchlater()
    user_id = db.current_user(session['__auth'])
    films = db.watch_later(user_id)
    return render_template('watchlater.html', films=films)


@app.route('/watchlater/<film_id>')
@login_required
def watch_later(film_id):
    db_f = Film()
    if not db_f.check_film(film_id):
        return render_template('404.html')
    db = Watchlater()
    user_id = db.current_user(session['__auth'])
    if not db.check_duplicate(user_id, film_id):
        db.add_watch_later(user_id, film_id)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/watchlater/<film_id>/delete')
@login_required
def del_watch_later(film_id):
    db = Watchlater()
    user_id = db.current_user(session['__auth'])
    if db.check_duplicate(user_id, film_id):
        db.delete_watchlater(user_id, film_id)
        return redirect(url_for('movie', film_id=film_id))
    return render_template('404.html')


@app.route('/favorites')
@login_required
def favorites_list():
    db = Favorites()
    user_id = db.current_user(session['__auth'])
    films = db.favorites(user_id)
    return render_template('favorites.html', films=films)


@app.route('/favorite/<film_id>')
@login_required
def favorite(film_id):
    db_f = Film()
    if not db_f.check_film(film_id):
        return render_template('404.html')
    db = Favorites()
    user_id = db.current_user(session['__auth'])
    if not db.check_duplicate(user_id, film_id):
        db.add_favorites(user_id, film_id)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/favorite/<film_id>/delete')
@login_required
def del_favorites(film_id):
    db = Favorites()
    user_id = db.current_user(session['__auth'])
    if db.check_duplicate(user_id, film_id):
        db.delete_favorites(user_id, film_id)
        return redirect(url_for('movie', film_id=film_id))
    return render_template('404.html')


@app.route('/genres')
def genres():
    genres = tuple(request.args.getlist('gen'))
    page = request.args.get('page', '1')
    search = Search()
    films, page, pageCount, filmsCount = search.films_by_genres(genres, page)
    return render_template('genres.html', films=films, page=page,
                           pageCount=pageCount, filmsCount=filmsCount,
                           genres=genres)


@app.route('/rate/<film_id>/<val>')
@login_required
def rate_movie(film_id, val):
    film = Film()
    user = User()
    if not film.check_film(film_id):
        return render_template("404.html")
    if not user.check_rate(film_id):
        user.rate(film_id, val)
        film.rate(film_id, val)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/delete_rate/<film_id>')
@login_required
def delete_rate(film_id):
    film = Film()
    user = User()
    if not film.check_film(film_id):
        return render_template("404.html")
    if user.check_rate(film_id):
        val = user.delete_rate(film_id)
        film.delete_rate(film_id, val)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/flows/add/<film_id>', methods=['GET', 'POST'])
@login_required
def new_filmInlist(film_id):
    username = session["__auth"]
    form = WatchlistForm(username)
    db = Watchlist()
    if form.validate_on_submit():
        list_name = form.title.data
        body = form.content.data
        if request.form.get("mycheckbox"):
            db.add_watchlist(username, list_name, body)
            list_id = db.get_list_id(username, session['__auth'], list_name)
            db.add_film(list_id, film_id)
        else:
            db.add_watchlist(username, list_name, body)
        return redirect(url_for("movie", film_id=film_id))
    return render_template('newlist.html', form=form,
                           title="New Flow", checkbox=True)


@app.route('/flows/add', methods=['GET', 'POST'])
@login_required
def new_watchlist():
    username = session["__auth"]
    form = WatchlistForm(username)
    db = Watchlist()
    if form.validate_on_submit():
        list_name = form.title.data
        body = form.content.data
        db.add_watchlist(username, list_name, body)
        return redirect(url_for("watchlists", username=username))
    return render_template('newlist.html', form=form, title="New Flow", )


@app.route('/flow/<list_name>/add/<film_id>')
@login_required
def add_filmInList(list_name, film_id):
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    list_id = db.get_list_id(username, session['__auth'], list_name)
    db.add_film(list_id, film_id)
    return redirect(url_for('movie', film_id=film_id))


@app.route('/<username>/flows')
@login_required
def watchlists(username):
    db = Watchlist()
    user = User()
    id = user.current_user(username)
    if not id:
        return render_template('404.html')
    watchlists = db.watchlists(session['__auth'], username)
    return render_template('watchlist.html', watchlists=watchlists,
                           username=username)


@app.route('/flow/<list_name>/private')
@login_required
def private_list(list_name):
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    db.private_list(username, list_name)
    return redirect(url_for("watchlists", username=username))


@app.route('/flow/<list_name>/public')
@login_required
def public_list(list_name):
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    db.public_list(username, list_name)
    return redirect(url_for("watchlists", username=username))


@app.route('/<username>/flow/<list_name>')  # update
@login_required
def list_films(username, list_name):
    db = Watchlist()
    list_id = db.get_list_id(session['__auth'], username, list_name)
    if list_id is None:
        return render_template('404.html')
    films, watchlist = db.watchlist_films(list_id)
    return render_template('list_films.html', list_name=list_name, films=films,
                           username=username, watchlists=watchlist)


@app.route('/flow/<list_name>/delete')
@login_required
def del_watchlist(list_name):
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    list_id = db.get_list_id(username, session['__auth'], list_name)
    db.delete_watchlist(list_id)
    return redirect(url_for("watchlists", username=username))


@app.route('/flow/<list_name>/<film_id>/delete')
@login_required
def del_watchlist_film(list_name, film_id):
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    list_id = db.get_list_id(username, session['__auth'], list_name)
    db.delete_film(list_id, film_id)
    return redirect(url_for('list_films', list_name=list_name,
                            username=username))


@app.route('/flow/<list_name>/update', methods=['GET', 'POST'])
@login_required
def update_list(list_name):
    username = session["__auth"]
    form = UpdateList(username, list_name)
    db = Watchlist()
    username = session['__auth']
    if not db.check_watchlist(username, list_name):
        return render_template('404.html')
    elif form.validate_on_submit():
        list_title = form.title.data
        body = form.content.data
        list_id = db.get_list_id(username, session['__auth'], list_name)
        db.update_watchlist(list_id, list_title, body, username)
        return redirect(url_for("watchlists", username=username))
    form.title.data = list_name
    form.content.data = db.get_list_body(username, list_name)
    return render_template('newlist.html', form=form, title="Update Flow")
