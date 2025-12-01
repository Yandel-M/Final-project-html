import os
from flask import Flask, redirect, url_for, render_template, request, flash
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import time
import json

# --- Firestore and Firebase Setup ---
from firebase_admin import credentials, initialize_app
from firebase_admin import firestore
import firebase_admin

# --- Environment Configuration ---
FLASK_SECRET_KEY_ENV = os.environ.get("FLASK_SECRET_KEY", "super_secret_blog_key_123")
app_id = os.environ.get('__app_id', 'default-app-id')
firebase_config_json = os.environ.get('__firebase_config', '{}')

# Collection path for users and posts
USER_COLLECTION = f'artifacts/{app_id}/public/data/site_users'
POST_COLLECTION = f'artifacts/{app_id}/public/data/blog_posts'

# --- Initial Seed Data (Generic College Content) ---
INITIAL_POSTS_DATA = [
    {
        "id": 1,
        "title": "Welcome to The College Blog!",
        "author": "Yandel ",
        "content": "Hello, welcome to the official college blog! I hope you enjoy this website and what it has to offer.\r\nFind new people, connect, share with friends!\r\n\r\nHave a great day!",
        "timestamp": "2025-11-01 at 02:40:33",
        "likes": 1,
        "comments": [
            {
                "author": "Anonymous",
                "content": "Thanks I definitely will!",
                "timestamp": "2025-11-01 at 03:05:32"
            }
        ]
    },
    {
        "id": 2,
        "title": "Robotics Club Fall Showcase",
        "author": "Paxton Lavigne",
        "content": "The Campus Robotics team is having their robot reveal event on November 22nd in the project hall of the engineering building on campus. You should come and see the robot as this will be the first time we show it off to the public and it will be awesome!",
        "timestamp": "2025-11-01 at 11:13:07",
        "likes": 1,
        "comments": []
    },
    {
        "id": 3,
        "title": "Life at the University!",
        "author": "Jack",
        "content": "This is my second year at the university, and I love it here. I always feel like there is something to do on campus, whether with friends or solo, I never feel bored. Like the recent Fall Festival event, it was really fun and cool to go, with music, games, and food. It was really enjoyable to go.",
        "timestamp": "2025-11-01 at 11:25:54",
        "likes": 0,
        "comments": [
            {
                "author": "Yandel",
                "content": "It's my second year too. Campus is never boring. If you're bored, all you need to do is look in the right places!",
                "timestamp": "2025-11-01 at 11:27:25"
            }
        ]
    }
]

def parse_custom_timestamp(ts_str):
    """Converts the custom timestamp string into a standard UNIX timestamp (float)."""
    try:
        # Format: "YYYY-MM-DD at HH:MM:SS"
        dt_obj = datetime.strptime(ts_str, "%Y-%m-%d at %H:%M:%S")
        return dt_obj.timestamp()
    except Exception:
        # Fallback to current time if parsing fails
        return time.time() 

def seed_initial_data():
    """Seeds the Firestore database with initial posts if the collection is empty."""
    if not db:
        return
        
    try:
        posts_ref = db.collection(POST_COLLECTION)
        
        # Check if any documents exist (limit 1 for efficiency)
        if not posts_ref.limit(1).get():
            print("Seeding database with initial post data...")
            for post_data in INITIAL_POSTS_DATA:
                # Transform the data structure for Firestore
                doc_data = {
                    'title': post_data['title'],
                    'content': post_data['content'],
                    'author_username': post_data['author'], # Using 'author' from seed data
                    'likes_count': post_data['likes'],
                    'comments': post_data['comments'],
                    'created_at': parse_custom_timestamp(post_data['timestamp']),
                    'updated_at': parse_custom_timestamp(post_data['timestamp']),
                    'author_id': 'seed_user_id', # Placeholder ID for seeded content
                }
                posts_ref.add(doc_data)
            print("Database seeding complete.")
        else:
            print("Database already contains posts. Seeding skipped.")
            
    except Exception as e:
        print(f"Error during database seeding: {e}")


# --- Firebase Admin SDK Initialization (Server-side) ---
try:
    if not firebase_admin._apps:
        firebase_config = json.loads(firebase_config_json)
        cred_data = {
            "type": "service_account",
            "project_id": firebase_config.get("projectId"),
            "private_key_id": os.environ.get("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.environ.get("FIREBASE_PRIVATE_KEY", "").replace('\\n', '\n'),
            "client_email": os.environ.get("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.environ.get("FIREBASE_CLIENT_ID"),
        }
        
        if all(cred_data.values()):
            cred = credentials.Certificate(cred_data)
            initialize_app(cred, {'projectId': firebase_config.get("projectId")})
            db = firestore.client()
            print("Firestore initialized successfully.")
            # --- CALL SEEDING FUNCTION HERE ---
            seed_initial_data()
        else:
            print("WARNING: Firestore initialization skipped due to missing credentials.")
            db = None

    else:
        db = firestore.client()
        
except Exception as e:
    print(f"FATAL: Firestore Initialization Failed: {e}")
    db = None

# --- Flask and Configuration (Rest of app.py is the same) ---
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY_ENV
app.config["PREFERRED_URL_SCHEME"] = "http" 

# --- Flask-Login Setup (Same) ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'warning'

# Custom User Class for Flask-Login (Same)
class User(UserMixin):
    def __init__(self, user_id, username, email, role='standard'):
        self.id = user_id
        self.username = username
        self.email = email
        self.role = role

    def is_admin(self):
        return self.role == 'admin'

    @staticmethod
    def get_by_id(user_id):
        if not db: return None
        try:
            doc_ref = db.collection(USER_COLLECTION).document(user_id).get()
            if doc_ref.exists:
                data = doc_ref.to_dict()
                return User(user_id=user_id, username=data.get('username'), email=data.get('email'), role=data.get('role', 'standard'))
        except Exception as e:
            print(f"Error fetching user {user_id}: {e}")
            return None
        return None

    @staticmethod
    def get_by_username(username):
        if not db: return None, None
        try:
            users_ref = db.collection(USER_COLLECTION)
            query = users_ref.where('username', '==', username).limit(1).get()
            if query:
                user_doc = query[0]
                data = user_doc.to_dict()
                return User(user_id=user_doc.id, username=data.get('username'), email=data.get('email'), role=data.get('role', 'standard')), data.get('password_hash')
        except Exception as e:
            print(f"Error querying user by username: {e}")
            return None, None
        return None, None

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)

@app.context_processor
def inject_user_status():
    return dict(is_logged_in=current_user.is_authenticated, current_user=current_user)

# --- Routes (Same) ---

@app.route('/')
def index():
    # --- FETCH TOP 3 POSTS FOR HOMEPAGE ---
    if not db:
        flash('Cannot retrieve posts: Database connection failed.', 'danger')
        return render_template('homepage.html', posts=[])
        
    posts = []
    try:
        posts_ref = db.collection(POST_COLLECTION)
        # Fetch up to 10 posts to ensure we get 3 even if some data is bad, then sort in Python.
        query_results = posts_ref.get() 
        
        for doc in query_results:
            post = doc.to_dict()
            post['id'] = doc.id
            post['created_at_dt'] = datetime.fromtimestamp(post.get('created_at', 0))
            posts.append(post)
            
        # Sort posts by timestamp in descending order (latest first)
        posts.sort(key=lambda p: p['created_at'], reverse=True)
        
        # Limit to top 3 posts for the homepage
        top_posts = posts[:3]
            
    except Exception as e:
        flash('Error fetching blog posts for homepage.', 'danger')
        print(f"Error fetching index posts: {e}")
        top_posts = []

    return render_template('homepage.html', posts=top_posts)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

# --- Post Viewing (All Posts) ---
@app.route('/view_posts')
def view_posts():
    # --- FETCH ALL POSTS ---
    if not db:
        flash('Cannot retrieve posts: Database connection failed.', 'danger')
        return render_template('posts.html', posts=[]) # Updated to posts.html
        
    posts = []
    try:
        posts_ref = db.collection(POST_COLLECTION)
        query_results = posts_ref.get()
        
        for doc in query_results:
            post = doc.to_dict()
            post['id'] = doc.id
            post['created_at_dt'] = datetime.fromtimestamp(post.get('created_at', 0))
            posts.append(post)
            
        # Sort posts by timestamp in descending order (latest first)
        posts.sort(key=lambda p: p['created_at'], reverse=True)
            
    except Exception as e:
        flash('Error fetching blog posts.', 'danger')
        print(f"Error fetching posts: {e}")

    return render_template('posts.html', posts=posts) # Updated to posts.html

# --- Post Creation (Same) ---
@app.route('/create_post', methods=['GET', 'POST'])
@login_required 
def create_post():
    if not current_user.is_admin():
        flash('You must be an administrator to create a post.', 'danger')
        return redirect(url_for('view_posts'))
        
    if request.method == 'POST':
        if not db:
            flash('Database connection is not available. Cannot create post.', 'danger')
            return render_template('create_post.html')

        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return render_template('create_post.html', title=title, content=content)

        try:
            post_data = {
                'title': title,
                'content': content,
                'author_id': current_user.id,
                'author_username': current_user.username,
                # New posts start with 0 likes and no comments
                'likes_count': 0, 
                'comments': [],
                'created_at': time.time(),
                'updated_at': time.time()
            }
            
            db.collection(POST_COLLECTION).add(post_data)
            
            flash('Post created successfully!', 'success')
            return redirect(url_for('view_posts'))

        except Exception as e:
            flash('An error occurred while saving the post.', 'danger')
            print(f"Firestore Post Creation Error: {e}")
            return render_template('create_post.html', title=title, content=content)

    return render_template('create_post.html')

# --- User Authentication (Same) ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        flash('You are already signed up and logged in!', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')

        if not db:
            flash('Database connection is not available. Please check server logs.', 'danger')
            return render_template('signup.html')

        try:
            if db.collection(USER_COLLECTION).where('username', '==', username).limit(1).get():
                flash('Username already taken. Please choose another.', 'danger')
                return render_template('signup.html')

            password_hash = generate_password_hash(password)

            user_data = {
                'username': username,
                'email': email,
                'password_hash': password_hash,
                'role': 'standard',
                'created_at': time.time()
            }
            
            new_user_ref = db.collection(USER_COLLECTION).add(user_data)
            user_doc_id = new_user_ref[1].id

            new_user = User(user_id=user_doc_id, username=username, email=email, role='standard')
            login_user(new_user)

            flash(f'Account created successfully! Welcome, {username}.', 'success')
            return redirect(url_for('index'))

        except Exception as e:
            flash('An error occurred during sign up. Please try again.', 'danger')
            print(f"Firestore Sign Up Error: {e}")
            return render_template('signup.html')

    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        flash('You are already logged in!', 'info')
        return redirect(url_for('index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not db:
            flash('Database connection is not available. Cannot log in.', 'danger')
            return render_template('login.html')

        try:
            user, password_hash = User.get_by_username(username)
            
            if user and check_password_hash(password_hash, password):
                login_user(user)
                flash(f'Welcome back, {username}!', 'success')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.', 'danger')

        except Exception as e:
            print(f"Firestore Login Error: {e}")
            flash('An error occurred during login. Please try again.', 'danger')

    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('index'))

# --- Error Handlers (Same) ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)