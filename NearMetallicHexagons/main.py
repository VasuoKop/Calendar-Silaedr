from flask import Flask, render_template, request, redirect, url_for
import calendar
from datetime import datetime
app = Flask(__name__)
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        month = int(request.form['month'])
        year = int(request.form['year'])
    else:
        now = datetime.now()
        month = now.month
        year = now.year
        current_day = now.day
    cal_html = calendar.HTMLCalendar().formatmonth(year, month)
    return render_template('index.html', cal_html=cal_html, month=month, year=year, current_day=current_day)
@app.route('/calendar')
def get_calendar():
    month = int(request.args.get('month'))
    year = int(request.args.get('year'))
    cal_html = calendar.HTMLCalendar().formatmonth(year, month)
    return cal_html
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)