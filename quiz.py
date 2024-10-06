import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from db_scripts import get_next_question, check_answer, get_quizes, create_user, \
    get_user_by_username, verify_password
from random import shuffle
import sqlite3

app = Flask(__name__)
app.config["SECRET_KEY"] = "ThisIsSuperSecretKey"
app.template_folder = os.path.join(os.getcwd(), 'templates')
app.static_folder = os.path.join(os.getcwd(), 'static')


def start_quiz(quiz_id):
    """Инициализация параметров викторины"""
    if isinstance(quiz_id, int):  # Проверяем, что quiz_id - это целое число
        session["quiz"] = quiz_id
        session["last_question"] = 0
        session["answers"] = 0
        session["total"] = 0


def end_quiz():
    """Очистка сессии после завершения викторины только для неавторизованных пользователей"""
    if 'user_id' not in session:  # Если пользователь не авторизован
        session.clear()


def get_form_quizes():
    """Получение списка викторин и рендеринг главной страницы"""
    quizes = get_quizes()
    return render_template("index.html", quizes=quizes)


def get_user_by_id(user_id):
    """Получение информации о пользователе по его идентификатору"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute(
        'SELECT username, achievements, level, points, completed_victories, selected_avatar FROM users WHERE id = ?',
        (user_id,))
    user = cursor.fetchone()
    conn.close()
    return user


def get_form_question(question):
    """Рендеринг вопроса"""
    answers = [question[2], question[3], question[4], question[5]]
    shuffle(answers)  # Перемешиваем варианты ответов
    return render_template('test.html', question=question[1], question_id=question[0], answers=answers)


def get_user_data():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    cursor.execute('SELECT username, achievements, avatar, level, points, completed_victories FROM users')
    users = cursor.fetchall()

    conn.close()
    return users


def save_answer():
    """Сохранение ответа на вопрос"""
    answer = request.form.get('answer')  # Получение ответа пользователя
    question_id = request.form.get('question_id')
    session['last_question'] = question_id
    session['total'] += 1  # Обновление общего количества вопросов
    if check_answer(question_id, answer):  # Проверка правильности ответа
        session["answers"] += 1  # Увеличиваем счётчик правильных ответов


def increment_completed_victories(user_id):
    """Увеличение количества завершенных викторин для пользователя"""
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        UPDATE users
        SET completed_victories = completed_victories + 1
        WHERE id = ?
    ''', (user_id,))
    conn.commit()
    conn.close()


def update_user_stats(user_id, completed_victory=False, is_perfect=False):
    """Обновление статистики пользователя:
       - Начисление монет (100 монет за 50%+ правильных ответов, 200 монет за 100%)
       - Увеличение уровня за каждую вторую пройденную викторину на 100%.
    """
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Получаем текущие данные пользователя
    cursor.execute('SELECT level, points, completed_victories FROM users WHERE id = ?', (user_id,))
    user_data = cursor.fetchone()
    current_level = user_data[0]
    current_points = user_data[1]
    completed_victories = user_data[2]

    # Определяем количество монет
    if is_perfect:
        new_points = current_points + 200  # Начисляем 200 монет за 100% правильных ответов
        completed_victories += 1  # Увеличиваем количество пройденных викторин
        # Повышаем уровень каждые 2 пройденные викторины на 100%
        if completed_victories % 2 == 0:
            current_level += 1
    else:
        new_points = current_points + 100  # Начисляем 100 монет за 50%+ правильных ответов

    # Обновляем данные в базе данных
    cursor.execute('''
        UPDATE users 
        SET level = ?, points = ?, completed_victories = ? 
        WHERE id = ?
    ''', (current_level, new_points, completed_victories, user_id))

    conn.commit()
    conn.close()


@app.route("/", methods=["GET", "POST"])
def index():
    """Главная страница с выбором викторины"""
    if request.method == "GET":
        start_quiz(-1)  # Инициализация сессии с пустой викториной
        return get_form_quizes()
    elif request.method == "POST":
        quiz_id = request.form.get("quiz")
        if quiz_id and quiz_id.isdigit():
            start_quiz(int(quiz_id))  # Запуск викторины
        return redirect(url_for('test'))  # Перенаправление на страницу теста


@app.route("/test", methods=["GET", "POST"])
def test():
    """Страница с тестом"""
    if "quiz" in session and int(session["quiz"]) >= 0:
        if request.method == "POST":
            save_answer()  # Сохраняем ответ на предыдущий вопрос
        question = get_next_question(session["last_question"], session["quiz"])  # Получаем следующий вопрос
        if question is None or len(question) == 0:  # Если вопросы закончились
            return redirect(url_for("result"))  # Перенаправляем на страницу результатов
        else:
            return get_form_question(question)  # Показываем следующий вопрос
    else:
        return redirect(url_for("index"))  # Возврат на главную, если не выбрана викторина


@app.route("/result")
def result():
    """Страница с результатами викторины"""
    if 'answers' not in session or 'total' not in session:
        return redirect(url_for("index"))  # Защита от прямого перехода

    correct_answers = session['answers']
    total_questions = session['total']

    # Определяем процент правильных ответов
    percentage = (correct_answers / total_questions) * 100

    # Начисляем монеты и обновляем уровень в зависимости от результатов
    if 'user_id' in session:
        if percentage == 100:  # Если 100% правильных ответов
            update_user_stats(session['user_id'], completed_victory=True, is_perfect=True)
        elif percentage >= 50:  # Если больше 50% правильных ответов
            update_user_stats(session['user_id'], completed_victory=True, is_perfect=False)

    html = render_template("result.html", right=correct_answers, total=total_questions)  # Отображаем результаты
    end_quiz()  # Очищаем сессию только для неавторизованных пользователей
    return html


@app.route('/buy_avatar/<avatar_name>', methods=['POST'])
def buy_avatar(avatar_name):
    if 'user_id' not in session:  # Проверка, авторизован ли пользователь
        return redirect(url_for('login'))

    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Получаем информацию о пользователе
    cursor.execute('SELECT points, avatar_list, selected_avatar FROM users WHERE id = ?', (session['user_id'],))
    user = cursor.fetchone()

    if not user:
        return redirect(url_for('shop'))

    # Список доступных аватарок и их цены
    avatars_data = {
        'avatar1': 2000,
        'avatar2': 4000,
        'avatar3': 7000,
        'avatar4': 15000,
        'avatar5': 2000,
        'avatar6': 4000,
        'avatar7': 700,
        'avatar8': 15000
    }

    if avatar_name not in avatars_data:
        return redirect(url_for('shop'))

    avatar_price = avatars_data[avatar_name]

    # Проверяем, достаточно ли монет у пользователя
    user_points = user[0]  # Индекс 0 — это поле points
    owned_avatars = user[1].split(',')  # Индекс 1 — это поле avatar_list
    selected_avatar = user[2]  # Индекс 2 — это поле selected_avatar

    if avatar_name in owned_avatars:
        return redirect(url_for('shop'))

    if user_points >= avatar_price:
        # Обновляем монеты и добавляем купленный аватар в список
        new_points = user_points - avatar_price
        owned_avatars.append(avatar_name)
        new_avatar_list = ','.join(owned_avatars)

        cursor.execute('UPDATE users SET points = ?, avatar_list = ? WHERE id = ?',
                       (new_points, new_avatar_list, session['user_id']))
        conn.commit()

    conn.close()
    return redirect(url_for('shop'))


# Маршрут для установки аватарки
@app.route('/set_avatar', methods=['POST'])
def set_avatar():
    if 'user_id' not in session:  # Проверяем авторизацию
        return redirect(url_for('login'))

    avatar_name = request.form['avatar']
    conn = sqlite3.connect('database.db')

    # Обновляем выбранную аватарку
    conn.execute('UPDATE users SET selected_avatar = ? WHERE id = ?',
                 (avatar_name + '.png', session['user_id']))
    conn.commit()

    conn.close()
    return redirect(url_for('shop'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Обработка логина"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = get_user_by_username(username)

        if user and verify_password(user[2], password):  # Проверяем пароль
            session['user_id'] = user[0]
            session['username'] = user[1]
            return redirect(url_for('index'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Обработка регистрации"""
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        if create_user(username, password):  # Создаем нового пользователя
            return redirect(url_for('login'))
        else:
            flash('Такой логин уже существует!', 'danger')

    return render_template('register.html')


@app.route('/stats')
def stats():
    """Страница статистики. Доступна только для авторизованных пользователей."""
    if 'user_id' not in session:  # Если пользователь не авторизован
        return redirect(url_for('login'))  # Перенаправление на страницу входа

    # Получаем данные пользователя для отображения статистики
    user_id = session['user_id']
    user = get_user_by_id(user_id)

    if user is None:
        return redirect(url_for('login'))

    return render_template('stats.html', user=user)


@app.route('/shop')
def shop():
    if 'user_id' not in session:  # Проверяем авторизацию
        return redirect(url_for('login'))

    # Получаем данные о пользователе
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row  # Используем Row для доступа к полям как к словарю
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()

    if not user:
        flash('Пользователь не найден.', 'error')
        return redirect(url_for('login'))

    # Доступные аватарки и их цены
    avatars_data = [
        {'name': 'avatar1', 'image': 'avatar1.png', 'price': 2000},
        {'name': 'avatar2', 'image': 'avatar2.png', 'price': 4000},
        {'name': 'avatar3', 'image': 'avatar3.png', 'price': 7000},
        {'name': 'avatar4', 'image': 'avatar4.png', 'price': 15000},
        {'name': 'avatar5', 'image': 'avatar5.png', 'price': 2000},
        {'name': 'avatar6', 'image': 'avatar6.png', 'price': 4000},
        {'name': 'avatar7', 'image': 'avatar7.png', 'price': 7000},
        {'name': 'avatar8', 'image': 'avatar8.png', 'price': 15000}
    ]

    # Если у пользователя нет аватарок или список пуст, создаем пустой список
    owned_avatars = user['avatar_list'].split(',') if user['avatar_list'] else []

    # Формируем список аватаров с информацией о владении и выборе
    user_avatars = []
    for avatar in avatars_data:
        is_owned = avatar['name'] in owned_avatars
        is_selected = avatar['name'] + '.png' == user['selected_avatar']
        user_avatars.append({
            'name': avatar['name'],
            'image': 'static/' + avatar['image'],  # Правильный путь до изображения
            'price': avatar['price'],
            'is_owned': is_owned,
            'is_selected': is_selected
        })

    conn.close()

    # Передаем данные в шаблон
    return render_template('shop.html', user_coins=user['points'], avatars=user_avatars, user=user)


@app.route('/logout')
def logout():
    """Выход из аккаунта"""
    session.pop('user_id', None)
    session.pop('username', None)
    flash('Вы успешно вышли из аккаунта.', 'success')
    return redirect(url_for('index'))


def get_data():
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM data')
    rows = cursor.fetchall()
    columns = [desc[0] for desc in cursor.description]
    conn.close()
    return columns, rows


if __name__ == "__main__":
    app.run(debug=True)
