import os
from flask import Flask, redirect, url_for, render_template, request, flash
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import time
import json

# --- Environment Configuration ---
FLASK_SECRET_KEY_ENV = os.environ.get("FLASK_SECRET_KEY", "super_secret_blog_key_123")
app_id = os.environ.get('__app_id', 'default-app-id')

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

# --- Flask and Configuration (Rest of app.py is the same) ---
app = Flask(__name__)
app.secret_key = FLASK_SECRET_KEY_ENV
app.config["PREFERRED_URL_SCHEME"] = "http" 

# --- Routes (Same) ---

@app.route('/')
def index():
    # --- FETCH TOP 3 POSTS FOR HOMEPAGE ---
    posts = []
    # Load from data.json
    try:
        with open('data.json', 'r') as f:
            json_posts = json.load(f)
            for post in json_posts:
                # Convert timestamp string to datetime for sorting
                post['created_at'] = time.mktime(time.strptime(post['timestamp'], '%Y-%m-%d at %H:%M:%S'))
                post['created_at_dt'] = datetime.fromtimestamp(post['created_at'])
                posts.append(post)
            # Sort posts by timestamp in descending order (latest first)
            posts.sort(key=lambda p: p['created_at'], reverse=True)
    except Exception as e:
        print(f"Error loading posts from data.json: {e}")
        flash('Error loading blog posts.', 'danger')
    
    # Limit to top 3 posts for the homepage
    top_posts = posts[:3]
            
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
    posts = []
    # Load from data.json
    try:
        with open('data.json', 'r') as f:
            json_posts = json.load(f)
            for post in json_posts:
                # Convert timestamp string to datetime for sorting
                post['created_at'] = time.mktime(time.strptime(post['timestamp'], '%Y-%m-%d at %H:%M:%S'))
                post['created_at_dt'] = datetime.fromtimestamp(post['created_at'])
                posts.append(post)
            # Sort posts by timestamp in descending order (latest first)
            posts.sort(key=lambda p: p['created_at'], reverse=True)
    except Exception as e:
        print(f"Error loading posts from data.json: {e}")
        flash('Error loading blog posts.', 'danger')

    return render_template('posts.html', posts=posts) # Updated to posts.html

# --- Post Creation (Same) ---
@app.route('/create_post', methods=['GET', 'POST'])
def create_post():
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        
        if not title or not content:
            flash('Title and content are required.', 'danger')
            return render_template('create-posts.html', title=title, content=content)

        try:
            # Save to data.json
            try:
                with open('data.json', 'r') as f:
                    posts = json.load(f)
                
                # Get next id
                max_id = max([p['id'] for p in posts]) if posts else 0
                new_id = max_id + 1
                
                # Format timestamp like existing posts
                timestamp_str = datetime.now().strftime('%Y-%m-%d at %H:%M:%S')
                
                new_post = {
                    'id': new_id,
                    'title': title,
                    'author': 'Anonymous',
                    'content': content,
                    'timestamp': timestamp_str,
                    'likes': 0,
                    'comments': []
                }
                
                posts.append(new_post)
                
                with open('data.json', 'w') as f:
                    json.dump(posts, f, indent=4)
                    
            except Exception as e:
                flash('Error saving post to local data.', 'danger')
                print(f"Error saving to data.json: {e}")
                return render_template('create-posts.html', title=title, content=content)
            
            flash('Post created successfully!', 'success')
            return redirect(url_for('view_posts'))

        except Exception as e:
            flash('An error occurred while saving the post.', 'danger')
            print(f"Post Creation Error: {e}")
            return render_template('create-posts.html', title=title, content=content)

    return render_template('create-posts.html')

# --- Comment Addition ---
@app.route('/add_comment/<int:post_id>', methods=['POST'])
def add_comment(post_id):
    author = request.form.get('author', 'Anonymous')
    content = request.form.get('content')
    
    if not content:
        flash('Comment content is required.', 'danger')
        return redirect(url_for('view_posts'))
    
    try:
        # Load existing posts
        with open('data.json', 'r') as f:
            posts = json.load(f)
        
        # Find the post
        post = next((p for p in posts if p['id'] == post_id), None)
        if not post:
            flash('Post not found.', 'danger')
            return redirect(url_for('view_posts'))
        
        # Add the comment
        comment = {
            'author': author,
            'content': content,
            'timestamp': datetime.now().strftime('%Y-%m-%d at %H:%M:%S')
        }
        post['comments'].append(comment)
        
        # Save back to file
        with open('data.json', 'w') as f:
            json.dump(posts, f, indent=4)
        
        flash('Comment added successfully!', 'success')
        
    except Exception as e:
        flash('Error adding comment.', 'danger')
        print(f"Error adding comment: {e}")
    
    return redirect(url_for('view_posts'))

# --- User Authentication (Same) ---

# --- Error Handlers (Same) ---
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)