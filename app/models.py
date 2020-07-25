import sqlite3
import hashlib
from math import ceil
from functools import wraps
from flask import g, url_for, session, redirect, flash
from app import app
from datetime import datetime
from dateutil import relativedelta


class DataBase:
    def get_db(self):
        db = g.get('db')
        if db is None:
            db = sqlite3.connect('app.db')
            db.row_factory = sqlite3.Row
            g.db = db
        return db

    def get_time_after_posting(self, date_time):
        delta_values = ('years', 'months', 'days',
                        'hours', 'minutes', 'seconds')
        mask = {'years': 'yr', 'months': 'mo', 'days': 'd',
                'hours': 'hr', 'minutes': 'min', 'seconds': 'sec'}
        current_time = datetime.utcnow()
        posting_time = datetime.strptime(date_time, "%Y-%m-%d %H:%M:%S")
        difference = relativedelta.relativedelta(current_time, posting_time)
        for delta_value in delta_values:
            res = getattr(difference, delta_value)
            if res:
                return f"{res} {mask[delta_value]}"
        return "0 sec"


class Film(DataBase):
    def __init__(self):
        with app.app_context():
            self.db = super().get_db()

    def check_film(self, id):
        cur = self.db.cursor()
        film = cur.execute("SELECT id FROM films WHERE id = :Id LIMIT 1",
                           {"Id": id}).fetchone()
        return True if film else False

    def get_top_movies(self):
        cur = self.db.cursor()
        return cur.execute("""SELECT * FROM films
                           ORDER BY value DESC LIMIT 100""").fetchall()

    def get_popular_movies(self):
        cur = self.db.cursor()
        return cur.execute("""SELECT * FROM films WHERE year > 2018
                           ORDER BY value DESC LIMIT 40""").fetchall()

    def get_film(self, id, page):
        cur = self.db.cursor()
        id = {"Id": id}
        film = cur.execute("SELECT * FROM films WHERE id = :Id",
                           id).fetchone()

        directors = cur.execute("""SELECT persons.id, persons.name FROM persons
        LEFT JOIN films_casts ON persons.id = films_casts.person_id
        WHERE film_id = :Id and films_casts.type = 1""",
                                id).fetchall()

        actors = cur.execute("""SELECT persons.id, persons.name FROM persons
        LEFT JOIN films_casts on persons.id = films_casts.person_id
        WHERE film_id = :Id and films_casts.type = 2""",
                             id).fetchall()

        genres = cur.execute("""SELECT genres.genre FROM genres LEFT JOIN
        films_genres on films_genres.genre_id = genres.id LEFT JOIN films
        on films.id = films_genres.film_id WHERE films.id = :Id""",
                             id).fetchall()

        reviews, page, all_pages = self.__get_reviews(id, page)

        return film, directors, actors, genres, reviews, page, all_pages

    def __get_reviews(self, id, page):
        cur = self.db.cursor()
        reviews = []
        if not page.isdigit() or page == '0':
            page = '1'
        page = int(page) - 1
        reviews_count = cur.execute("""SELECT COUNT(id) FROM reviews
        WHERE film_id = :Id""", id).fetchone()[0]
        all_pages = ceil(reviews_count / app.config['REVIEWS_PER_PAGE'])
        if page * app.config['REVIEWS_PER_PAGE'] > reviews_count:
            page = 0

        start_reviews = cur.execute(f"""SELECT users.id, users.name,
        reviews.body, reviews.date FROM users LEFT JOIN reviews ON
        users.id = reviews.user_id WHERE film_id = :Id ORDER BY date DESC
        LIMIT {app.config['REVIEWS_PER_PAGE']} OFFSET
        {app.config['REVIEWS_PER_PAGE'] * page}""", id).fetchall()

        for review in start_reviews:
            date = super().get_time_after_posting(review['date'])
            reviews.append({'id': review['id'], 'name': review['name'],
                            'body': review['body'], 'date': date})
        return reviews, page+1, all_pages

    def highest_grossing_movies(self):
        cur = self.db.cursor()
        return cur.execute("""SELECT * FROM films ORDER BY
                              box_office DESC LIMIT 100""").fetchall()

    def write_review(self, body, user_id, film_id):
        cur = self.db.cursor()
        date = str(datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"))
        comment = {"User_id": user_id, "Film_id": film_id,
                   "Body": body, "Date": date}
        cur.execute("""INSERT INTO reviews (user_id, film_id, body, date)
                    VALUES(:User_id, :Film_id, :Body, :Date)""", comment)
        self.db.commit()

    def rate(self, id, val):
        if not val.isdigit() or int(val) < 1 or int(val) > 10:
            return None
        val = int(val)
        cur = self.db.cursor()
        rate, votes = cur.execute("""SELECT rate, votes FROM films
        WHERE id = :Id""", {'Id': id}).fetchone()
        rate = (rate * votes + val) / (votes + 1)
        to_db = {'Rate': rate,
                 'Votes': votes + 1,
                 'Id': id}
        cur.execute("""UPDATE films SET rate = :Rate,
                       votes = :Votes WHERE id = :Id""", to_db)
        self.db.commit()

    def delete_rate(self, id, val):
        val = int(val)
        cur = self.db.cursor()
        rate, votes = cur.execute("""SELECT rate, votes FROM films
        WHERE id = :Id""", {'Id': id}).fetchone()
        rate = (rate * votes - val) / (votes - 1)
        to_db = {'Rate': rate,
                 'Votes': votes - 1,
                 'Id': id}
        cur.execute("""UPDATE films SET rate = :Rate,
                       votes = :Votes WHERE id = :Id""", to_db)
        self.db.commit()


class Person(DataBase):
    def __init__(self):
        with app.app_context():
            self.db = super().get_db()

    def check_person(self, id):
        cur = self.db.cursor()
        person = cur.execute("SELECT id FROM persons WHERE id = :Id ",
                             {"Id": id}).fetchone()
        return True if person else False

    def person_info(self, id):
        cur = self.db.cursor()
        id = {"Id": id}
        jobs = cur.execute("""SELECT type FROM types LEFT JOIN persons_types
                              ON persons_types.type_id=types.id
                              WHERE person_id = :Id""", id).fetchone()
        person = cur.execute("""SELECT * FROM persons
                             WHERE id = :Id""", id).fetchone()

        as_director = cur.execute("""SELECT films.id, films.title FROM films
                                  LEFT JOIN  films_casts on
                                  films.id=films_casts.film_id
                                  WHERE person_id=:Id AND type=1""",
                                  id).fetchall()
        as_actor = cur.execute("""SELECT films.id, films.title FROM films
                                  LEFT JOIN  films_casts
                                  on films.id=films_casts.film_id
                                  WHERE person_id=:Id AND type=2""",
                               id).fetchall()
        if as_actor == []:
            as_actor = None
        if as_director == []:
            as_director = None
        return person, as_actor, as_director, jobs


class User(DataBase):
    def __init__(self):
        with app.app_context():
            self.db = super().get_db()

    def set_password(self, password):
        return hashlib.pbkdf2_hmac(
            'sha256', bytes(password, 'utf8'),
            app.config.get("SALT"), 150000).hex()

    def check_user(self, name, password):
        password = self.set_password(password)
        cur = self.db.cursor()
        wpass = {"Name": name, "Pass": password}
        wpass = cur.execute("""SELECT password FROM users
                            WHERE name = :Name and password = :Pass LIMIT 1""",
                            wpass).fetchone()
        return True if wpass else False

    def validate_name(self, name):
        name = {"Name": name}
        cur = self.db.cursor()
        user = cur.execute("SELECT name FROM users WHERE name = :Name LIMIT 1",
                           name).fetchone()
        return False if user else True

    def validate_email(self, email):
        cur = self.db.cursor()
        email = {"Email": email}
        mail = cur.execute("""SELECT email FROM users
                           WHERE email = :Email LIMIT 1""", email).fetchone()
        return False if mail else True

    def insert_user(self, name, email, password):
        cur = self.db.cursor()
        password = self.set_password(password)
        user = {"Name": name, "Email": email, "Password": password}
        cur.execute("""INSERT INTO users (name, email, password)
                    VALUES(:Name, :Email, :Password)""", user)
        self.db.commit()

    def current_user(self, name):
        name = {"Name": name}
        cur = self.db.cursor()
        res = cur.execute('SELECT id FROM users '
                          'WHERE name = :Name', name).fetchone()
        return res[0] if res else None

    def check_rate(self, film_id):
        cur = self.db.cursor()
        id = self.current_user(session['__auth'])
        rate = cur.execute('SELECT rate FROM films_rates '
                           'WHERE user_id = :User_id AND film_id = :Film_id',
                           {'User_id': id, 'Film_id': film_id}).fetchone()
        return rate['rate'] if rate else 0

    def rate(self, film_id, val):
        cur = self.db.cursor()
        if not val.isdigit() or int(val) < 1 or int(val) > 10:
            return None
        user_id = self.current_user(session['__auth'])
        cur.execute("""INSERT INTO films_rates (film_id, user_id, rate)
                    VALUES(?, ?, ?)""", (film_id, user_id, val))
        self.db.commit()

    def delete_rate(self, film_id):
        cur = self.db.cursor()
        user_id = self.current_user(session['__auth'])
        rate = cur.execute(
            'SELECT rate FROM films_rates WHERE '
            'user_id = ? AND film_id = ?', (user_id, film_id)).fetchone()[0]
        cur.execute("""DELETE FROM films_rates WHERE
                       user_id = ? AND film_id = ?""", (user_id, film_id))
        self.db.commit()
        return rate

    def follow(self, following):
        if self.is_following(following):
            return None
        cur = self.db.cursor()
        user_id = self.current_user(session['__auth'])
        foll_id = self.current_user(following)
        cur.execute("""INSERT INTO followed (is_following, following)
                       VALUES(?, ?)""", (user_id, foll_id))
        self.db.commit()

    def unfollow(self, following):
        if not self.is_following(following):
            return None
        cur = self.db.cursor()
        user_id = self.current_user(session['__auth'])
        foll_id = self.current_user(following)
        cur.execute("""DELETE FROM followed WHERE
                    is_following=? AND following=?""", (user_id, foll_id))
        self.db.commit()

    def followers(self, username):
        user_id = self.current_user(username)
        cur = self.db.cursor()
        foll_names = cur.execute("""SELECT users.name FROM followed LEFT JOIN
                                 users ON users.id = followed.is_following
                                 WHERE following=?""", (user_id,)).fetchall()
        return foll_names if foll_names else []

    def followings(self, username):
        user_id = self.current_user(username)
        cur = self.db.cursor()
        foll_names = cur.execute("""SELECT users.name FROM followed LEFT JOIN
                                 users ON users.id = followed.following WHERE
                                 is_following=?""", (user_id,)).fetchall()
        return foll_names if foll_names else []

    def is_following(self, following):
        cur = self.db.cursor()
        user_id = self.current_user(session['__auth'])
        foll_id = self.current_user(following)
        res = cur.execute("""SELECT id FROM followed WHERE
                          is_following = ? and
                          following = ?""", (user_id, foll_id)).fetchone()
        return True if res else False

    def get_reviews(self, id, page):
        cur = self.db.cursor()
        id = {"Id": id}
        reviews = []
        if not page.isdigit() or page == '0':
            page = '1'
        page = int(page) - 1
        reviews_count = cur.execute("""SELECT COUNT(id) FROM reviews
        WHERE user_id = :Id""", id).fetchone()[0]
        if page * app.config['REVIEWS_PER_PAGE'] > reviews_count:
            page = 0

        start_reviews = cur.execute(f"""SELECT films.id, films.title, films.rate,
        films.img, reviews.body, reviews.date FROM films LEFT JOIN reviews ON
        films.id = reviews.film_id WHERE user_id = :Id ORDER BY date DESC
        LIMIT {app.config['REVIEWS_PER_PAGE']} OFFSET
        {app.config['REVIEWS_PER_PAGE'] * page}""", id).fetchall()

        all_pages = ceil(len(start_reviews) / app.config['REVIEWS_PER_PAGE'])

        for review in start_reviews:
            date = super().get_time_after_posting(review['date'])
            reviews.append({'id': review['id'], 'name': review['title'],
                            'body': review['body'], 'date': date,
                            'rate': review['rate'], 'img': review['img']})
        return reviews, page+1, all_pages


class Watchlist(User):
    def __init__(self):
        super().__init__()

    def check_watchlist(self, username, list_name):
        cur = self.db.cursor()
        watchlist = cur.execute("""SELECT id FROM watchlists WHERE
                                   name=? and username=?""",
                                (list_name, username)).fetchone()
        return True if watchlist else False

    def watchlists(self, guest, username):
        cur = self.db.cursor()
        if username == guest:
            watchlists = cur.execute("""SELECT * FROM watchlists
                                     WHERE username=?  ORDER BY id DESC""",
                                     (username,)).fetchall()
        else:
            watchlists = cur.execute("""SELECT * FROM watchlists WHERE
                                     username=? and private=0 ORDER BY
                                     id DESC""", (username,)).fetchall()
        return watchlists

    def add_watchlist(self, username, list_name, body):
        cur = self.db.cursor()
        cur.execute("""INSERT INTO watchlists (username, name, body) \
                           VALUES(?,?,?)""", (username, list_name, body))
        self.db.commit()

    def get_list_id(self, guest, username, list_name):  # update
        cur = self.db.cursor()
        if username == guest:
            list_id = cur.execute("""SELECT id FROM watchlists
                                  WHERE username=? and name=?""",
                                  (username, list_name)).fetchall()
        else:
            list_id = cur.execute("""SELECT id FROM watchlists
                                  WHERE username=? and name=? and private=0""",
                                  (username, list_name)).fetchall()
        return None if not list_id else list_id[0]['id']

    def private_list(self, username, list_name):
        cur = self.db.cursor()
        cur.execute("""UPDATE watchlists SET private=1 \
                   WHERE name=? and username=?""", (list_name, username))
        self.db.commit()

    def public_list(self, username, list_name):
        cur = self.db.cursor()
        cur.execute("""UPDATE watchlists SET private=0 \
                      WHERE name=? and username=?""", (list_name, username))
        self.db.commit()

    def add_film(self, list_id, film_id):
        cur = self.db.cursor()
        ok = cur.execute("""SELECT id FROM watchlists_films
                            WHERE watchlist_id=? and film_id=?""",
                         (list_id, film_id)).fetchone()
        if not ok:
            cur.execute("""INSERT INTO watchlists_films (watchlist_id, film_id) \
                           VALUES(?,?) """, (list_id, film_id))
            self.db.commit()

    def watchlist_films(self, list_id):
        cur = self.db.cursor()
        films = cur.execute("""SELECT films.id, films.img, films.title FROM
        films LEFT JOIN watchlists_films on film_id=films.id WHERE
        watchlists_films.watchlist_id=? ORDER BY watchlists_films.id""",
                            (list_id,)).fetchall()
        watchlist = cur.execute("""SELECT * FROM watchlists WHERE id=?""",
                                (list_id,)).fetchone()
        return films, watchlist

    def watchlist_names(self, username):
        cur = self.db.cursor()
        return cur.execute("""SELECT id, name FROM watchlists
                              WHERE username=? ORDER BY id DESC""",
                           (username,)).fetchall()

    def delete_watchlist(self, list_id):
        cur = self.db.cursor()
        cur.execute("""DELETE FROM watchlists_films WHERE watchlist_id=?""",
                    (list_id,))
        cur.execute("""DELETE FROM watchlists WHERE id=?""", (list_id,))
        self.db.commit()

    def update_watchlist(self, list_id, list_name, body, username):
        cur = self.db.cursor()
        cur.execute("""DELETE FROM watchlists WHERE username=? and id=?""",
                    (username, list_id))
        cur.execute("""INSERT INTO watchlists (id, name, body, username)
                       VALUES(?,?,?,?)""",
                    (list_id, list_name, body, username))
        self.db.commit()

    def delete_film(self, list_id, film_id):
        cur = self.db.cursor()
        cur.execute("""DELETE FROM watchlists_films WHERE
                       watchlist_id=? and film_id=?""", (list_id, film_id))
        self.db.commit()

    def get_list_body(self, username, list_name):
        cur = self.db.cursor()
        return cur.execute("""SELECT body FROM watchlists
                              WHERE name=? and username=?""",
                           (list_name, username)).fetchone()[0]

    def validate_listname(self, username, list_name):
        cur = self.db.cursor()
        name = cur.execute("""SELECT name FROM watchlists
                               WHERE name=? and username=? """,
                           (list_name, username)).fetchone()
        return False if name else True


class Watchlater(User):
    def __init__(self):
        super().__init__()

    def watch_later(self, user_id):
        cur = self.db.cursor()
        films = cur.execute("""SELECT * FROM films LEFT JOIN users_watchlater \
                              on film_id=films.id WHERE user_id=? \
                             ORDER BY users_watchlater.id DESC""",
                            (user_id,)).fetchall()
        return films

    def add_watch_later(self, user_id, film_id):
        cur = self.db.cursor()
        cur.execute("""INSERT INTO users_watchlater (user_id, film_id)
                    VALUES(?,?)""", (user_id, film_id))
        self.db.commit()

    def check_duplicate(self, user_id, film_id):
        cur = self.db.cursor()
        watchlater = cur.execute("""SELECT * FROM users_watchlater \
                                 WHERE user_id=? and film_id=?""",
                                 (user_id, film_id)).fetchone()
        return bool(watchlater)

    def delete_watchlater(self, user_id, film_id):
        cur = self.db.cursor()
        cur.execute("""DELETE  FROM users_watchlater \
                       WHERE user_id=? and film_id=?""", (user_id, film_id))
        self.db.commit()


class Favorites(User):
    def __init__(self):
        super().__init__()

    def favorites(self, user_id):
        cur = self.db.cursor()
        films = cur.execute("""SELECT * FROM films LEFT JOIN users_favorites \
                            on film_id=films.id WHERE user_id=? \
                            ORDER BY users_favorites.id DESC""",
                            (user_id,)).fetchall()
        return films

    def add_favorites(self, user_id, film_id):
        cur = self.db.cursor()
        cur.execute("""INSERT INTO users_favorites (user_id, film_id)
                    VALUES(?,?)""", (user_id, film_id))
        self.db.commit()

    def check_duplicate(self, user_id, film_id):
        cur = self.db.cursor()
        favorites = cur.execute("""SELECT * FROM users_favorites \
                                WHERE user_id=? and film_id=?""",
                                (user_id, film_id)).fetchone()
        return bool(favorites)

    def delete_favorites(self, user_id, film_id):
        cur = self.db.cursor()
        cur.execute("""DELETE  FROM users_favorites \
                       WHERE user_id=? and film_id=?""", (user_id, film_id))
        self.db.commit()


class Search(DataBase):
    def __init__(self):
        with app.app_context():
            self.db = super().get_db()

    def search__user(self, name):
        cur = self.db.cursor()
        name = name.replace('"', "")
        name = name.replace("%", "")
        if name == '':
            return list()
        usernames = cur.execute(f"""SELECT name, id, SUM(cis_following) as
        followings, SUM(cfollowing) as followers FROM(SELECT users.name,
        users.id, COUNT(followed.following) as cis_following, 0 as cfollowing
        FROM users LEFT JOIN followed ON followed.is_following=users.id
        WHERE upper(users.name) LIKE "{name}%" GROUP by users.name
        UNION ALL
        SELECT users.name, users.id, 0, COUNT(followed.following) as cfollowing
        FROM users LEFT JOIN followed ON followed.following=users.id WHERE
        upper(users.name) LIKE "{name}%" GROUP by users.name) as res_tab
        GROUP by res_tab.id ORDER by SUM(cfollowing) DESC
        LIMIT {app.config['USERS_SEARCH_LIMIT']}""").fetchall()
        return usernames

    def search_film(self, title, page):
        cur = self.db.cursor()
        if not page.isdigit() or page == '0':
            page = '1'
        page = int(page) - 1
        title = title.replace('"', "")
        title = title.replace("%", "")
        if title == '':
            return list(), 1, 0
        films_number = cur.execute(f"""SELECT COUNT(id) FROM films
                                    WHERE upper(title) LIKE
                                    "{title.upper()}%" """).fetchone()[0]
        if page * app.config['ITEMS_PER_PAGE'] > films_number:
            page = 0
        films = cur.execute(
                            f"""SELECT * FROM films WHERE upper(title)
                            LIKE "{title.upper()}%" ORDER BY year DESC,
                            value DESC LIMIT {app.config['ITEMS_PER_PAGE']}
                            OFFSET {app.config['ITEMS_PER_PAGE'] * page}"""
                            ).fetchall()
        return films, page+1, films_number

    def search_person(self, name, page, types):
        cur = self.db.cursor()
        if not page.isdigit() or page == '0':
            page = '1'
        page = int(page) - 1
        name = name.replace('"', "")
        name = name.replace("%", "")
        if name == '':
            return list(), 1, 0
        persons_number = cur.execute(f"""SELECT COUNT(id) FROM persons
                                    WHERE upper(name) LIKE
                                    "{name.upper()}%" """).fetchone()[0]
        if page * app.config['ITEMS_PER_PAGE'] > persons_number:
            page = 0
        query_mask = """SELECT persons.id, persons.img, persons.name FROM
        persons LEFT JOIN persons_types ON persons.id = persons_types.person_id
        WHERE upper(persons.name) LIKE "{}%" AND persons_types.type_id= {}"""
        query = " UNION ".join([query_mask.format(name, id) for id in types])
        persons = cur.execute(f"""{query} ORDER BY persons.name LIMIT
        {app.config['ITEMS_PER_PAGE']} OFFSET
        {app.config['ITEMS_PER_PAGE'] * page}""").fetchall()
        return persons, page+1, persons_number

    def __get_genres_ids(self, genres):
        cur = self.db.cursor()
        genres = "({})".format((','.join(f'"{genre}"' for genre in genres)))
        return cur.execute(f"""SELECT id FROM genres WHERE \
                               LOWER(genre) IN {genres}""").fetchall()

    def films_by_genres(self, genres, page):
        cur = self.db.cursor()
        ids = self.__get_genres_ids(genres)
        if not ids:
            return [], 1, 1, 0
        if not page.isdigit() or page == '0':
            page = '1'
        page = int(page) - 1
        query_mask = """SELECT film_id FROM films_genres \
                        WHERE genre_id = {}"""
        query = " INTERSECT ".join([query_mask.format(id['id']) for id in ids])
        films_number = cur.execute(f"""SELECT COUNT(*) FROM
                                       ({query})""").fetchone()[0]
        if page * app.config['ITEMS_PER_PAGE'] > films_number:
            page = 0
        query_mask = """SELECT films.title, films.img, films.rate, films.value,
                        films.year, films.id FROM films LEFT JOIN films_genres
                        ON films.id = films_genres.film_id
                        WHERE genre_id = {}"""
        query = " INTERSECT ".join([query_mask.format(id['id']) for id in ids])
        films = cur.execute(f"""{query} ORDER by year DESC, value DESC LIMIT {app.config['ITEMS_PER_PAGE']}
        OFFSET {app.config['ITEMS_PER_PAGE'] * page}""").fetchall()
        return (films, page+1,
                ceil(films_number / app.config['ITEMS_PER_PAGE']),
                films_number)


def login_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if '__auth' not in session:
            flash('Login required')
            return redirect(url_for('login_get'))
        return func(*args, **kwargs)

    return wrapper


def logout_required(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        if '__auth' in session:
            flash('Logout required')
            return redirect(url_for('index'))
        return func(*args, **kwargs)

    return wrapper
