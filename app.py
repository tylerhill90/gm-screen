#!/usr/bin/env python3

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session, url_for
from flask_session import Session
from passlib.apps import custom_app_context as pwd_context
from tempfile import mkdtemp
from flask_sqlalchemy import SQLAlchemy
import datetime


def apology(message, code=400):
    """Renders message as an apology to user."""
    def escape(s):
        """
        Escape special characters.

        https://github.com/jacebrowning/memegen#special-characters
        """
        for old, new in [("-", "--"), (" ", "-"), ("_", "__"), ("?", "~q"),
                         ("%", "~p"), ("#", "~h"), ("/", "~s"), ("\"", "''")]:
            s = s.replace(old, new)
        return s
    return render_template("apology.html", top=code, bottom=escape(message)), code


# configure application
app = Flask(__name__)


# ensure responses aren't cached
if app.config["DEBUG"]:
    @app.after_request
    def after_request(response):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Expires"] = 0
        response.headers["Pragma"] = "no-cache"
        return response

# configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = True
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


class Config(object):
    SQLALCHEMY_DATABASE_URI = 'sqlite:///GMScreen.db?check_same_thread=True'


# configure CS50 Library to use SQLite database
db = SQL("sqlite:///GMscreen.db")


@app.route("/", methods=["GET", "POST"])
def index():

    # do some stuff

    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # check passwords match
        if not request.form.get('password') == request.form.get('password_match'):
            return apology('Password fields must match')

        # if user input correct then store the user's info in the database after hashing their password
        else:
            hash = pwd_context.hash(request.form.get('password'))
            result = db.execute("INSERT INTO users (username, hash) VALUES(:username, :hash)",
                                username=request.form.get('username'), hash=hash)
            if not result:
                return apology('Failure to signup new user.')
            else:
                return render_template('login.html')

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in."""

    # forget any user_id
    session.clear()

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # ensure username exists and password is correct
        if len(rows) != 1 or not pwd_context.verify(request.form.get("password"), rows[0]["hash"]):
            return apology("invalid username and/or password")

        # remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # redirect user to home page
        return redirect(url_for("account"))

    # else if user reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/account", methods=["GET", "POST"])
def account():
    """User's account."""

    # get username
    query = db.execute(
        'SELECT username FROM users WHERE id=:user_id', user_id=session["user_id"])
    username = query[0]['username']

    # get campaign names
    query = db.execute(
        'SELECT campaign_name FROM campaigns WHERE user_id=:user_id', user_id=session["user_id"])
    campaigns = [query[x]['campaign_name'].strip(
        "'") for x in range(len(query))]

    print(query)

    return render_template("account.html", username=username, campaigns=campaigns)


@app.route("/logout")
def logout():
    """Log user out."""

    # forget any user_id
    session.clear()

    # redirect user to login form
    return redirect(url_for("index"))


@app.route("/campaign_editor", methods=["GET", "POST"])
def campaign_editor():
    """Edit a new or old campaign."""

    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # if user is editing a new campaign with a distinct name, display and store its name
        query = db.execute(
            'SELECT * FROM campaigns WHERE user_id=:user_id', user_id=session["user_id"])
        if len(query) > 0 and request.form['new_camp'] == query[0]['campaign_name'].strip("'"):
            return apology('That campaign name already exists for this account. Please choose a distinct name.')

        elif request.form['new_camp']:
            session["camp_name"] = request.form['new_camp']
            db.execute('INSERT INTO "campaigns" ("id","user_id","campaign_name") VALUES (NULL,:user_id,:camp_name)',
                       user_id=session["user_id"], camp_name=session["camp_name"])
            session["camp_id"] = db.execute('SELECT id FROM campaigns WHERE user_id=:user_id AND campaign_name=:camp_name',
                                            user_id=session["user_id"], camp_name=session["camp_name"])

            return render_template("campaign_editor.html", camp_name=session["camp_name"].strip("'"), chars=[], camp_id=session["camp_id"])

        else:
            return apology('Sorry. An error occurred. Please try again.')

    # else if user reached route via GET (as by clicking a link or via redirect) and is editing an existing campaign
    else:
        # query db for existing characters in the appropriate campaign
        chars = db.execute(
            'SELECT id, name, race, class, spell_save, ac, hp FROM characters WHERE campaign_id=:camp_id', camp_id=session["camp_id"])

        for char in chars:
            for key, value in char.items():
                if type(value) is str:
                    char[key] = value.strip("'")

        return render_template("campaign_editor.html", camp_name=session["camp_name"].strip("'"), chars=chars, camp_id=session["camp_id"])


@app.route("/play_campaign", methods=["GET", "POST"])
def play_campaign():
    """Play a campaign."""

    # cache campaign name
    session["camp_name"] = request.form['play_camp']

    # Query db for correct campaign_id and cache it
    query = db.execute('SELECT * FROM campaigns WHERE user_id=:user_id AND campaign_name=:camp_name',
                       user_id=session["user_id"], camp_name=session["camp_name"])
    session["camp_id"] = query[0]['id']

    # Query db for existing characters in the appropriate campaign
    chars = db.execute(
        'SELECT name, race, class, spell_save, ac, hp FROM characters WHERE campaign_id=:camp_id', camp_id=session["camp_id"])
    for char in chars:
        for key, value in char.items():
            char[key] = value.strip("'")

    return render_template("play_campaign.html", camp_name=session["camp_name"].strip("'"), chars=chars)


@app.route("/store_char", methods=["GET", "POST"])
def store_char():
    """Store a new character in the db."""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if request.form['name']:
            # query db for correct campaign_id and cache it
            query = db.execute('SELECT * FROM campaigns WHERE user_id=:user_id AND campaign_name=:camp_name',
                               user_id=session["user_id"], camp_name=session["camp_name"])
            session["camp_id"] = query[0]['id']

            # store new character infor in db
            name, race, class_, spell_save, ac, hp = request.form['name'], request.form['race'], request.form[
                'class'], request.form['spell_save'], request.form['ac'], request.form['hp']
            db.execute('INSERT INTO "characters" ("id","campaign_id","name","race","class", "spell_save", "ac","hp") VALUES (NULL,:camp_id,:name,:race,:class_,:spell_save,:ac,:hp)',
                       camp_id=session["camp_id"], name=name, race=race, class_=class_, spell_save=spell_save, ac=ac, hp=hp)

            return redirect(url_for("campaign_editor"))

    else:
        return redirect(url_for("campaign_editor"))


@app.route("/retrieve_old_campaign", methods=["GET", "POST"])
def retrieve_old_campaign():
    """Retrieve an old campaign and pass it to the editor page"""
    # if user reached route via POST (as by submitting a form via POST)
    if request.method == "POST":
        if request.form['old_camp']:
            session["camp_name"] = request.form['old_camp']

            # query db for correct campaign_id and cache it
            query = db.execute('SELECT * FROM campaigns WHERE user_id=:user_id AND campaign_name=:camp_name',
                               user_id=session["user_id"], camp_name=session["camp_name"])
            session["camp_id"] = query[0]['id']

            return redirect(url_for("campaign_editor"))

    else:
        return redirect(url_for("campaign_editor"))


@app.route("/edit_char", methods=["GET", "POST"])
def edit_char():
    """Edit a character."""

    # query db for existing characters in the appropriate campaign
    char = db.execute(
        'SELECT id, name, race, class, spell_save, ac, hp FROM characters WHERE id=:id_', id_=request.form['edit_char'])
    char = char[0]
    for key, value in char.items():
        if type(value) is str:
            char[key] = value.strip("'")

    return render_template("edit_char.html", char=char)


@app.route("/update_char", methods=["GET", "POST"])
def update_char():
    """Update an existing character."""

    name, race, class_, spell_save, ac, hp, id_ = request.form['name'], request.form['race'], request.form[
        'class'], request.form['spell_save'], request.form['ac'], request.form['hp'], request.form['id']
    db.execute('UPDATE characters SET name=:name, race=:race, class=:class_, spell_save=:spell_save, ac=:ac, hp=:hp WHERE id=:id_',
               name=name, race=race, class_=class_, spell_save=spell_save, ac=ac, hp=hp, id_=id_)

    return redirect(url_for("campaign_editor"))


@app.route("/delete_char", methods=["GET", "POST"])
def delete_char():
    """Update an existing character."""

    id_ = request.form['delete_char']
    db.execute('DELETE FROM characters WHERE id=:id_', id_=id_)

    return redirect(url_for("campaign_editor"))


if __name__ == "__main__":
    app.run(debug=False)
