import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

import time
import json
import os


app = Flask(__name__)



app.secret_key = 'super_secret_blog_key_123' 

Upload_folder = 'static/uploads'
allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
DATA_FILE = 'data.json'

app.config['UPLOAD_FOLDER'] = Upload_folder

blog_posts = []

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

def is_logged_in():
    return session.get('logged_in', False)

@app.context_processor
def inject_globals():
    return dict(is_logged_in=is_logged_in)


@app.route('/')
def index():
    sorted_posts = sorted(blog_posts, 
                          key=lambda x: datetime.datetime.strptime(x['timestamp'], "%Y-%m-%d at %H:%M:%S"), 
                          reverse=True)
                          
 
    latest_posts = sorted_posts[:3]
    

    return render_template('homepage.html', latest_posts=latest_posts)

@app.route('/create-posts', methods=['GET', 'POST'])
def create_post():
    """
    Handles both rendering the creation form (GET) and processing post submission (POST).
    Accessible to all users.
    """
    if request.method == 'POST':
        global blog_posts  

        title = request.form.get('post-title')
        author = request.form.get('post-author') or "Anonymous"
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
    comment_author = request.form.get('author') or "Anonymous"
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
def upload_file():
    
    if 'file' not in request.files:
        # Check if the file input name is 'files' or 'file'
        if 'files' not in request.files:
             flash('No file part in the request.', 'error')
             return redirect(request.url)
    
    # FIX 3: Assuming the input name is 'file', but checking for 'files' as in original code
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


        new_post = {
            'id': len(blog_posts) + 1, 
            'title': "Uploaded Image",
            'author': "Anonymous",
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


if __name__ == '__main__':
    os.makedirs(Upload_folder, exist_ok=True)
    app.run(debug=True)
