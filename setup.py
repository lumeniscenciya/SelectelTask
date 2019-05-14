from flask import Flask, jsonify, abort, request, make_response, session
import requests
from flaskext.mysql import MySQL
from flask_httpauth import HTTPBasicAuth
import logging
from time import strftime
import traceback
from logging.handlers import RotatingFileHandler

auth = HTTPBasicAuth()
app = Flask(__name__, static_url_path="")
app.secret_key = 'why would I tell you my secret key?'
mysql = MySQL()
#  Конфигурация MySQL
app.config['MYSQL_DATABASE_USER'] = 'userDB'
app.config['MYSQL_DATABASE_PASSWORD'] = '020896lumen'
app.config['MYSQL_DATABASE_DB'] = 'JokesDB'
app.config['MYSQL_DATABASE_HOST'] = 'aa6bkyeme6tejq.c1amhyf5jdyt.us-east-2.rds.amazonaws.com'
mysql.init_app(app)


@auth.get_password
def get_password(username):
    """
    Функция поиска имени пользователя в БД. 
    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tbl_users where tbl_users.user_name = %s", username)
    data = cursor.fetchone()
    session['UserId'] = data[0]
    conn.commit()
    if len(data) > 0:
        return 'python'
    return None


@auth.error_handler
def unauthorized():
    """
    Отлавливает неавторизованных пользователей.
    Выводит 'error': 'Unauthorized access', если пользователь не найден.
    """
    return make_response(jsonify({'error': 'Unauthorized access'}), 401)


@app.route('/todo/api/jokes/new', methods=['GET'])
@auth.login_required
def generate_joke():
    """
    Функция генерации новой шутки. 
    Проверяет уникальность сгенерированной шутки для данного пользователя и записывает её в БД.
    Выводит сгенерированную шутку.
    """
    data = requests.get('https://geek-jokes.sameerkumar.website/api')
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM tbl_jokes WHERE tbl_jokes.joke_text = %s and "
                   "tbl_jokes.joke_user_id = %s", (data.text, session.get('UserId')))
    answer = cursor.fetchone()
    if answer is not None:
        abort(400)
    cursor.execute("INSERT INTO tbl_jokes(joke_user_id, joke_text) VALUES(%s, %s)", (session.get('UserId'), data.text))
    conn.commit()
    return jsonify(data.json())


@app.route('/todo/api/jokes', methods=['GET'])
@auth.login_required
def get_jokes():
    """
    Функция показа всех шуток. 
    Возвращает все шутки данного пользователя из БД.
    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT tbl_jokes.joke_id, tbl_jokes.joke_text FROM tbl_jokes "
                   "WHERE tbl_jokes.joke_user_id = %s", session.get('UserId'))
    jokes = cursor.fetchall()
    conn.commit()
    return jsonify({'jokes': jokes})


@app.route('/todo/api/jokes/<int:joke_id>', methods=['GET'])
@auth.login_required
def get_joke(joke_id):
    """
    Функция показа шутки по Id. 
    Возвращает шутку по id пользователя и шутки.
    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT tbl_jokes.joke_text FROM tbl_jokes WHERE tbl_jokes.joke_user_id = %s and"
                   " tbl_jokes.joke_id= %s", (session.get('UserId'), joke_id))
    joke = cursor.fetchone()
    conn.commit()
    if joke is not None:
        return jsonify({'joke': joke[0]})
    abort(404)


@app.route('/todo/api/jokes/<int:joke_id>', methods=['PUT'])
@auth.login_required
def update_joke(joke_id):
    """
    Функция редактирования шутки по Id.
    Проверяет наличие шутки в БД.
    При наличии шутки в БД изменяет её. 
    Возвращает новый текст шутки.
    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT tbl_jokes.joke_text FROM tbl_jokes WHERE tbl_jokes.joke_user_id = %s and "
                   "tbl_jokes.joke_id= %s", (session.get('UserId'), joke_id))
    joke = cursor.fetchone()
    if joke is None: 
        abort(404)
    if not request.json:
        abort(400)
    cursor.execute("UPDATE tbl_jokes SET tbl_jokes.joke_text = %s WHERE tbl_jokes.joke_user_id = %s and"
                   " tbl_jokes.joke_id= %s", (request.json.get("text"), session.get('UserId'), joke_id))
    conn.commit()
    return jsonify({'joke': request.json.get("text")})


@app.route('/todo/api/jokes/<int:joke_id>', methods=['DELETE'])
@auth.login_required
def delete_joke(joke_id):
    """
    Функция удаления шутки по Id.
    Проверяет наличие шутки в БД.
    При наличии шутки в БД удаляет её. 
    Возвращает результат удаления.
    """
    conn = mysql.connect()
    cursor = conn.cursor()
    cursor.execute("SELECT tbl_jokes.joke_text FROM tbl_jokes WHERE tbl_jokes.joke_user_id = %s and"
                   " tbl_jokes.joke_id= %s", (session.get('UserId'), joke_id))
    joke = cursor.fetchone()
    if joke is None:
        abort(404)
    cursor.execute("DELETE FROM tbl_jokes WHERE tbl_jokes.joke_user_id = %s and"
                   " tbl_jokes.joke_id = %s", (session.get('UserId'), joke_id))
    conn.commit()
    return jsonify({'result': True})


@app.after_request
def after_request(response):
    """
    Функция логгирования действий пользователей.
    Записывает в app.log id пользователя, его ip адрес и время запроса
    """
    ts = strftime('[%H:%M %d-%b-%Y ]')
    logger.error('id: %s, ip: %s, time: %s', session.get('UserId'), request.remote_addr, ts)
    return response


@app.errorhandler(404)
def not_found(error):
    """
    Отлавливает ошибку 404
    """
    return make_response(jsonify({'error': 'Not found'}), 404)


@app.errorhandler(405)
def not_allowed(error):
    """
    Отлавливает ошибку 405
    """
    return make_response(jsonify({'error': 'Method Not Allowed'}), 405)


@app.errorhandler(400)
def bad_request(error):
    """
    Отлавливает ошибку 400
    """
    return make_response(jsonify({'error': 'Bad request'}), 400)


if __name__ == '__main__':
    handler = RotatingFileHandler('app.log', maxBytes=10000, backupCount=3)
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.ERROR)
    logger.addHandler(handler)
    app.run(debug=True)
