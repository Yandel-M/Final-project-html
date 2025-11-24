from flask import Bluepring, render_template, request, redirect, url_for, session, flash

website = Blueprint('website', __name__, static_folder='static', template_folder='templates')

@websiteRoute.route('/about')
def about():
    return render_template('about.html')

@websiteRoute.route('/contact')
def contact():
    return render_template('contact.html')

@websiteRoute.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            flash('Logged in successfully!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    return render_template('login.html')
