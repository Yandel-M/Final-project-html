import datetime
import os
import json
import time

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename
from functools import wraps

# --- Flask-Dance Imports for Google OAuth ---
from flask_dance.contrib.google import make_google_blueprint, google
from flask_dance.consumer.storage.session import SessionStorage
# --------------------------------------------

# --- Configuration ---

# NOTE: Replace these placeholders with your actual Client ID and Secret
# obtained from the Google Cloud Console.
GOOGLE_CLIENT_ID = "YOUR_GOOGLE_CLIENT_ID_HERE"
GOOGLE_CLIENT_SECRET = "YOUR_GOOGLE_CLIENT_SECRET_HERE"

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET_KEY", 'super_secret_blog_key_123') 
app.config["GOOGLE_OAUTH_CLIENT_ID"] = GOOGLE_CLIENT_ID
app.config["GOOGLE_OAUTH_CLIENT_SECRET"] = GOOGLE_CLIENT_SECRET


Upload_folder = 'static/uploads'
allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
DATA_FILE = 'data.json'

app.config['UPLOAD_FOLDER'] = Upload_folder

blog_posts = []

# --- Flask-Dance Blueprint Setup ---
google_bp = make_google_blueprint(
    client_id=GOOGLE_CLIENT_ID,
    client_secret=GOOGLE_CLIENT_SECRET,
    scope=["profile", "email"],
    # Redirect user to /posts after successful Google sign-in
    redirect_url="/posts" 
)
app.register_blueprint(google_bp, url_prefix="/login")
# ------------------------------------


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in allowed_extensions

def load_data():
    """Loads blog posts from the JSON file, handling empty/missing files."""
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            try:
                return json.load(f)
            except json.JSONDecodeError:
                return []
    return []

def save_data():
    """Saves blog posts to the JSON file."""
    with open(DATA_FILE, 'w') as f:
        json.dump(blog_posts, f, indent=4)


blog_posts = load_data()


# --- Custom User Management Helper ---

def get_current_user_info():
    """
    Checks if a user is logged in via Google OAuth and fetches/caches their info.
    Returns a dict with 'name' and 'email' or None.
    """
    # 1. Check for traditional simple login (if you keep it)
    if session.get('logged_in'):
        return {
            'name': session.get('username', 'Admin'), 
            'email': session.get('username', 'admin@local.com') # Using username for simulated email
        }

    # 2. Check for Google OAuth login
    if google.authorized:
        # Check session cache first
        if 'google_user_email' in session:
            return {
                'email': session['google_user_email'],
                'name': session.get('google_user_name', 'Google User')
            }

        # If authorized but no data, fetch from Google
        try:
            resp = google.get("/oauth2/v2/userinfo")
            if resp.ok:
                user_info = resp.json()
                # Store essential info in the session
                session['google_user_email'] = user_info['email']
                session['google_user_name'] = user_info.get('name', user_info['email'])
                return {
                    'email': user_info['email'],
                    'name': user_info.get('name', user_info['email'])
                }
            
            # If the response failed, clear authorization flag
            flash("Failed to retrieve profile data from Google.", "error")
            session.pop("google_oauth_token", None)
            return None

        except Exception as e:
            # Handle potential connection issues
            print(f"Error fetching Google user info: {e}")
            return None

    return None

def is_logged_in():
    """Returns True if any user (simple or Google) is logged in."""
    return get_current_user_info() is not None

# Add user info and login status to all templates
@app.context_processor
def inject_globals():
    return dict(
        is_logged_in=is_logged_in(),
        current_user=get_current_user_info()
    )

def login_required(f):
    """Decorator to protect routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not is_logged_in():
            flash("You must be logged in to access this page.", "error")
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    sorted_posts = sorted(blog_posts, 
                          key=lambda x: datetime.datetime.strptime(x['timestamp'], "%Y-%m-%d at %H:%M:%S"), 
                          reverse=True)
                          
    latest_posts = sorted_posts[:3]
    
    return render_template('homepage.html', latest_posts=latest_posts)

@app.route('/create-posts', methods=['GET', 'POST'])
@login_required # Protecting the post creation route
def create_post():
    """
    Handles both rendering the creation form (GET) and processing post submission (POST).
    Requires login.
    """
    current_user = get_current_user_info()
    
    if request.method == 'POST':
        global blog_posts  

        title = request.form.get('post-title')
        # Use the logged-in user's name for the author
        author = current_user.get('name', "Authenticated User")
        content = request.form.get('post-content')
        file = request.files.get('post-image')

        image_url = None

        if file and file.filename != '' and allowed_file(file.filename):
            try:
                timestamp = int(time.time())
                sanitized_name = secure_filename(file.filename)
                unique_filename = f"{timestamp}-{sanitized_name}" 
                
                file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
                file.save(file_path)

                image_url = url_for('static', filename=f'uploads/{unique_filename}')
                flash('Image uploaded successfully!', 'success')
            except Exception as e:
                flash(f'Error uploading image: {str(e)}', 'error')
                image_url = None
        

        current_time = datetime.datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

        new_post = {
            'id': len(blog_posts) + 1, 
            'title': title,
            'author': author,
            'content': content,
            'timestamp': current_time,
            'likes': 0,           
            'comments': [],    
            'image_url': image_url
        }
        
        blog_posts.append(new_post)
        save_data() 
        
        flash(f"Post '{title}' successfully created!", 'success')
        return redirect(url_for('view_posts'))

    return render_template('create-posts.html')


@app.route('/like-post/<int:post_id>', methods=['POST'])
def like_post(post_id):
    """Handles incrementing/decrementing the like count for a post."""
    
    # Keeping this open to non-logged-in users for simplicity, but tracking state in session
    liked_posts = session.get('liked_posts', [])
    
    post_to_update = next((post for post in blog_posts if post['id'] == post_id), None)

    if post_to_update:
        if post_id in liked_posts:
            post_to_update['likes'] -= 1
            liked_posts.remove(post_id)
            flash('Post unliked.', 'info')
        else:
            post_to_update['likes'] += 1
            liked_posts.append(post_id)
            flash('Post liked!', 'success')
        
        session['liked_posts'] = liked_posts
        save_data()
        
    return redirect(url_for('view_posts'))


@app.route('/add-comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    """Handles adding a new comment to a post."""
    current_user = get_current_user_info()
    
    # Use authenticated user name, fallback to form data or Anonymous
    comment_author = (current_user.get('name') if current_user else request.form.get('author')) or "Anonymous"
    comment_content = request.form.get('content')
    current_time = datetime.datetime.now().strftime("%Y-%m-%d at %H:%M:%S")

    post_to_update = next((post for post in blog_posts if post['id'] == post_id), None)

    if post_to_update and comment_content:
        new_comment = {
            'author': comment_author,
            'content': comment_content,
            'timestamp': current_time
        }
        post_to_update['comments'].append(new_comment)
        save_data() 
        flash('Comment added successfully!', 'success')
    else:
        flash('Could not add comment.', 'error')
        
    return redirect(url_for('view_posts'))

@app.route('/upload', methods=['POST'])
@login_required # Protecting the upload route
def upload_file():
    
    if 'file' not in request.files:
        if 'files' not in request.files:
             flash('No file part in the request.', 'error')
             return redirect(request.url)
    
    file = request.files.get('file') or request.files.get('files')

    if not file or file.filename == '':
        flash('No selected file.', 'error')
        return redirect(request.url)
    
    if file and allowed_file(file.filename):

        timestamp = int(time.time())
        extension = file.filename.rsplit('.', 1)[1].lower()
        unique_filename = secure_filename(f"{timestamp}.{extension}")

        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)

        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

        file.save(file_path)

        image_url = url_for('static', filename=f'uploads/{unique_filename}')

        try:
            with open(DATA_FILE, 'r') as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            data = []
            
        current_user = get_current_user_info()

        new_post = {
            'id': len(blog_posts) + 1, 
            'title': "Uploaded Image",
            'author': current_user.get('name', "Authenticated User"),
            'content': "Image uploaded via the file upload endpoint.",
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d at %H:%M:%S"),
            'likes': 0,
            'comments': [],
            'image_url': image_url
        }

        data.append(new_post)

        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        
        flash('File uploaded and saved as a post!', 'success')
        return redirect(url_for('index', success=True))
    
    flash('File upload failed or file type not allowed.', 'error')
    return redirect(request.url)
    

@app.route('/posts')
def view_posts():
    liked_posts = session.get('liked_posts', [])
    sorted_posts = sorted(blog_posts, key=lambda x: datetime.datetime.strptime(x['timestamp'], "%Y-%m-%d at %H:%M:%S"), reverse=True)
    
    return render_template('posts.html', posts=sorted_posts, liked_posts=liked_posts)


@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact')
def contact():
    return render_template('contact.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if is_logged_in():
        flash("You are already logged in.", "info")
        return redirect(url_for('view_posts'))

    if request.method == 'POST':
        # Traditional login handler (kept for compatibility)
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == 'admin' and password == 'password':
            session['logged_in'] = True
            session['username'] = username # Store username for the traditional user
            flash('Logged in successfully (Traditional)!', 'success')
            return redirect(url_for('index'))
        else:
            flash('Invalid credentials. Please try again.', 'error')
    
    # The login.html template should contain the "Sign in with Google" link
    return render_template('login.html')

@app.route("/logout")
def logout():
    # Clear traditional login session keys
    session.pop('logged_in', None)
    session.pop('username', None)

    # Clear Google OAuth session keys
    session.pop('google_user_email', None)
    session.pop('google_user_name', None)
    session.pop('google_oauth_token', None) # Clears the Flask-Dance token cache

    flash("You have been successfully logged out.", "success")
    return redirect(url_for("index"))


if __name__ == '__main__':
    os.makedirs(Upload_folder, exist_ok=True)
    app.run(debug=True)