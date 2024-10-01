import os
from flask import Flask, render_template, redirect, url_for, session, request, flash
from db_scripts import get_next_question, check_answer, get_quizes, get_quiz_count, get_random_quiz_id
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
    """Очистка сессии после завершения викторины"""
    session.clear()


def get_form_quizes():
    """Получение списка викторин и рендеринг главной страницы"""
    quizes = get_quizes()
    return render_template("index.html", quizes=quizes)


def get_form_question(question):
    """Рендеринг вопроса"""
    answers = [question[2], question[3], question[4], question[5]]
    shuffle(answers)  # Перемешиваем варианты ответов
    return render_template('test.html', question=question[1], question_id=question[0], answers=answers)


def save_answer():
    """Сохранение ответа на вопрос"""
    answer = request.form.get('answer')  # Получение ответа пользователя
    question_id = request.form.get('question_id')
    session['last_question'] = question_id
    session['total'] += 1  # Обновление общего количества вопросов
    if check_answer(question_id, answer):  # Проверка правильности ответа
        session["answers"] += 1  # Увеличиваем счётчик правильных ответов


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


@app.route('/login', methods=['GET', 'POST'])
def login():
    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    return render_template('register.html')


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
    html = render_template("result.html", right=session['answers'], total=session['total'])  # Отображаем результаты
    end_quiz()  # Очищаем сессию после завершения
    return html


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
