
from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import calendar
from datetime import datetime
import os
from werkzeug.security import generate_password_hash, check_password_hash
from database import User, Note, Classification, init_db, get_db, Base, engine

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY', 'your-secret-key')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if not username or not password:
            return render_template('register.html', error="Имя пользователя и пароль обязательны")
            
        try:
            with get_db() as db:
                if db.query(User).filter_by(username=username).first():
                    return render_template('register.html', error="Имя пользователя уже существует")
                    
                hashed_password = generate_password_hash(password)
                user = User(username=username, password=hashed_password)
                db.add(user)
                db.commit()
                return redirect(url_for('login'))
        except Exception as e:
            app.logger.error(f"Registration error: {str(e)}")
            return render_template('register.html', error="Регистрация не удалась. Попробуйте снова.")
            
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        with get_db() as db:
            user = db.query(User).filter_by(username=username).first()
            
            if user and check_password_hash(user.password, password):
                session['user_id'] = user.id
                session['username'] = user.username
                session['is_admin'] = user.is_admin == 1
                user.last_login = datetime.utcnow()
                db.commit()
                return redirect(url_for('index'))
            
            return render_template('login.html', error="Неверное имя пользователя или пароль")
            
    return render_template('login.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        month = int(request.form['month'])
        year = int(request.form['year'])
    else:
        now = datetime.now()
        month = now.month
        year = now.year
        
    return render_template('index.html', month=month, year=year)

@app.route('/calendar')
def get_calendar():
    if 'user_id' not in session:
        return redirect(url_for('login'))

    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    classification_filter = request.args.get('classification')

    if month < 1:
        month = 12
        year -= 1
    elif month > 12:
        month = 1
        year += 1

    cal = calendar.monthcalendar(year, month)
    month_names = ['', 'Январь', 'Февраль', 'Март', 'Апрель', 'Май', 'Июнь', 
                   'Июль', 'Август', 'Сентябрь', 'Октябрь', 'Ноябрь', 'Декабрь']
    month_name = month_names[month]

    html = f'''
    <caption>{month_name} {year}</caption>
    <tr><th>Пн</th><th>Вт</th><th>Ср</th><th>Чт</th><th>Пт</th><th>Сб</th><th>Вс</th></tr>
    '''

    for week in cal:
        html += '<tr>'
        for day in week:
            if day == 0:
                html += '<td></td>'
            else:
                date = datetime(year, month, day)
                notes = ''
                with get_db() as db:
                    if classification_filter:
                        # Filter notes by classification
                        day_notes = db.query(Note).filter_by(date=date).join(Note.classifications).filter(Classification.name == classification_filter).all()
                    else:
                        day_notes = db.query(Note).filter_by(date=date).all()

                    if day_notes:
                        notes = ' <span class="note-indicator">📝</span>'
                html += f'<td><div class="day-content">{day}{notes}</div></td>'
        html += '</tr>'

    return html

def is_admin():
    if 'user_id' not in session:
        return False
    return session.get('is_admin', False)

@app.route('/classifications', methods=['GET'])
def get_classifications():
    with get_db() as db:
        classifications = db.query(Classification).all()
        return jsonify([{'id': c.id, 'name': c.name} for c in classifications])

@app.route('/classification', methods=['POST'])
def add_classification():
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    name = request.form['name']
    with get_db() as db:
        classification = Classification(name=name)
        db.add(classification)
        db.commit()
        return jsonify({'success': True, 'id': classification.id})

@app.route('/note', methods=['POST'])
def add_note():
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    date = datetime.strptime(request.form['date'], '%Y-%m-%d')
    content = request.form['content']
    classification_ids = request.form.getlist('classification_ids[]')
    
    with get_db() as db:
        note = Note(user_id=session['user_id'], date=date, content=content)
        if classification_ids:
            classifications = db.query(Classification).filter(Classification.id.in_(classification_ids)).all()
            note.classifications = classifications
        db.add(note)
        db.commit()
        return jsonify({'success': True})

@app.route('/notes/<date>')
def get_notes(date):
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401

    date_obj = datetime.strptime(date, '%Y-%m-%d')
    classification_filter = request.args.get('classification')

    with get_db() as db:
        query = db.query(Note).filter_by(date=date_obj)
        if classification_filter:
            query = query.join(Note.classifications).filter(Classification.name == classification_filter)

        notes = query.all()
        result = []
        for note in notes:
            result.append({
                'id': note.id,
                'content': note.content,
                'user_id': note.user_id,
                'classifications': [{'id': c.id, 'name': c.name} for c in note.classifications]
            })
        return jsonify(result)

@app.route('/classification/<int:classification_id>', methods=['DELETE'])
def delete_classification(classification_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    with get_db() as db:
        classification = db.query(Classification).get(classification_id)
        if classification:
            for note in classification.notes:
                note.classification_id = None
            db.delete(classification)
            db.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'Категория не найдена'}), 404

@app.route('/note/<int:note_id>', methods=['DELETE'])
def delete_note(note_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    if not is_admin():
        return jsonify({'error': 'Требуется доступ администратора'}), 403
        
    with get_db() as db:
        note = db.query(Note).filter_by(
            id=note_id,
            user_id=session['user_id']
        ).first()
        
        if note:
            db.delete(note)
            db.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'Заметка не найдена'}), 404

@app.route('/users')
def users():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    with get_db() as db:
        all_users = db.query(User).all()
        return render_template('users.html', users=all_users)

@app.route('/userdatabase')
def userdatabase():
    if 'user_id' not in session or not is_admin():
        return redirect(url_for('login'))
    with get_db() as db:
        users = db.query(User).all()
        return render_template('userdatabase.html', users=users)

@app.route('/user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    if not is_admin():
        return jsonify({'error': 'Требуется доступ администратора'}), 403
    if user_id == session['user_id']:
        return jsonify({'error': 'Нельзя удалить самого себя'}), 400
    
    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            db.delete(user)
            db.commit()
            return jsonify({'success': True})
        return jsonify({'error': 'Пользователь не найден'}), 404

@app.route('/user/<int:user_id>/toggle-admin', methods=['POST'])
def toggle_admin(user_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Не авторизован'}), 401
    
    with get_db() as db:
        user = db.query(User).filter_by(id=user_id).first()
        if user:
            # Force toggle the status
            current_status = bool(user.is_admin)
            user.is_admin = 0 if current_status else 1
            db.commit()
            session['is_admin'] = bool(user.is_admin)
            return jsonify({'success': True, 'is_admin': user.is_admin == 1})
        return jsonify({'error': 'Пользователь не найден'}), 404

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

if __name__ == '__main__':
    with get_db() as db:
        Base.metadata.create_all(engine)
        # Create admin user if it doesn't exist
        admin = db.query(User).filter_by(username='Admin').first()
        if not admin:
            admin = User(
                username='Admin',
                password=generate_password_hash('123'),
                is_admin=1
            )
            db.add(admin)
            
            # Create default classifications
            default_classifications = ['Работа', 'Личное', 'Важное', 'Другое']
            for class_name in default_classifications:
                if not db.query(Classification).filter_by(name=class_name).first():
                    classification = Classification(name=class_name)
                    db.add(classification)
            
            db.commit()
    app.run(host='0.0.0.0', port=8080)
