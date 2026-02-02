from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
from datetime import datetime, timedelta
import json
import os
import math
import re
from collections import Counter

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this'

# File-based storage
USERS_FILE = 'users.json'
POSTS_FILE = 'posts.json'
COMMENTS_FILE = 'comments.json'
CATEGORIES_FILE = 'categories.json'
ANALYTICS_FILE = 'analytics.json'

# Pagination settings
POSTS_PER_PAGE = 6

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_users():
    return load_data(USERS_FILE)

def save_users(users):
    save_data(USERS_FILE, users)

def load_posts():
    return load_data(POSTS_FILE)

def save_posts(posts):
    save_data(POSTS_FILE, posts)

def load_comments():
    return load_data(COMMENTS_FILE)

def save_comments(comments):
    save_data(COMMENTS_FILE, comments)

def load_categories():
    return load_data(CATEGORIES_FILE)

def save_categories(categories):
    save_data(CATEGORIES_FILE, categories)

def load_analytics():
    return load_data(ANALYTICS_FILE)

def save_analytics(analytics):
    save_data(ANALYTICS_FILE, analytics)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session and 'admin_id' not in session:
            flash('Please log in to access this page.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_id' not in session or session.get('user_type') != 'admin':
            flash('Admin access required.', 'error')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

def user_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('user_type') != 'user':
            flash('User access required.', 'error')
            return redirect(url_for('user_login'))
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    users = load_users()
    
    # Check for admin session
    if 'admin_id' in session:
        user = next((u for u in users if u['id'] == session['admin_id']), None)
    # Check for user session
    elif 'user_id' in session:
        user = next((u for u in users if u['id'] == session['user_id']), None)
    else:
        return None
    
    if user:
        # Ensure all required fields exist
        if 'bio' not in user:
            user['bio'] = 'Platform Administrator' if user.get('is_admin') else ''
        if 'avatar' not in user:
            user['avatar'] = 'fas fa-user-shield' if user.get('is_admin') else 'fas fa-user'
        if 'last_login' not in user:
            user['last_login'] = None
    return user

def track_view(post_id, user_id=None):
    """Track post views for analytics"""
    analytics = load_analytics()
    today = datetime.now().strftime('%Y-%m-%d')
    
    if 'post_views' not in analytics:
        analytics['post_views'] = {}
    
    if str(post_id) not in analytics['post_views']:
        analytics['post_views'][str(post_id)] = {'total': 0, 'daily': {}}
    
    analytics['post_views'][str(post_id)]['total'] += 1
    
    if today not in analytics['post_views'][str(post_id)]['daily']:
        analytics['post_views'][str(post_id)]['daily'][today] = 0
    
    analytics['post_views'][str(post_id)]['daily'][today] += 1
    
    save_analytics(analytics)

def get_post_views(post_id):
    """Get total views for a post"""
    analytics = load_analytics()
    return analytics.get('post_views', {}).get(str(post_id), {}).get('total', 0)

def get_reading_time(content):
    """Calculate estimated reading time"""
    if not content:
        return 1
    words = len(str(content).split())
    minutes = max(1, round(words / 200))  # Average reading speed: 200 words per minute
    return minutes

def get_trending_posts(limit=5):
    """Get trending posts based on recent views"""
    analytics = load_analytics()
    posts = load_posts()
    
    # Get views from last 7 days
    recent_views = {}
    end_date = datetime.now()
    
    for post_id, data in analytics.get('post_views', {}).items():
        recent_count = 0
        for i in range(7):
            date = (end_date - timedelta(days=i)).strftime('%Y-%m-%d')
            recent_count += data.get('daily', {}).get(date, 0)
        
        if recent_count > 0:
            recent_views[int(post_id)] = recent_count
    
    # Sort posts by recent views
    trending_ids = sorted(recent_views.keys(), key=lambda x: recent_views[x], reverse=True)[:limit]
    trending_posts = [p for p in posts if p['id'] in trending_ids]
    
    return trending_posts

def get_related_posts(post, limit=3):
    """Get related posts based on tags and category"""
    posts = load_posts()
    current_tags = set(post.get('tags', []))
    current_category = post.get('category')
    
    scored_posts = []
    for p in posts:
        if p['id'] == post['id']:
            continue
            
        score = 0
        # Category match
        if p.get('category') == current_category:
            score += 3
        
        # Tag matches
        post_tags = set(p.get('tags', []))
        common_tags = current_tags.intersection(post_tags)
        score += len(common_tags) * 2
        
        if score > 0:
            scored_posts.append((p, score))
    
    # Sort by score and return top posts
    scored_posts.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in scored_posts[:limit]]

def search_posts(query, posts):
    """Enhanced search with relevance scoring"""
    if not query:
        return posts
    
    query_lower = query.lower()
    scored_posts = []
    
    for post in posts:
        score = 0
        
        # Title matches (higher weight)
        title_matches = len(re.findall(re.escape(query_lower), post['title'].lower()))
        score += title_matches * 3
        
        # Content matches
        content_matches = len(re.findall(re.escape(query_lower), post['content'].lower()))
        score += content_matches
        
        # Tag matches
        for tag in post.get('tags', []):
            if query_lower in tag.lower():
                score += 2
        
        # Category matches
        if post.get('category') and query_lower in post['category'].lower():
            score += 2
        
        if score > 0:
            scored_posts.append((post, score))
    
    # Sort by relevance score
    scored_posts.sort(key=lambda x: x[1], reverse=True)
    return [p[0] for p in scored_posts]

# Initialize default admin user
def init_admin():
    users = load_users()
    if not any(u.get('is_admin', False) for u in users):
        admin_user = {
            'id': 1,
            'username': 'admin',
            'email': 'admin@techinsight.pro',
            'password': generate_password_hash('admin123'),
            'is_admin': True,
            'bio': 'Platform Administrator',
            'avatar': 'fas fa-user-shield',
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'last_login': None
        }
        users.append(admin_user)
        save_users(users)
    else:
        # Update existing users to have required fields
        updated = False
        for user in users:
            if 'bio' not in user:
                user['bio'] = 'Platform Administrator' if user.get('is_admin') else ''
                updated = True
            if 'avatar' not in user:
                user['avatar'] = 'fas fa-user-shield' if user.get('is_admin') else 'fas fa-user'
                updated = True
            if 'last_login' not in user:
                user['last_login'] = None
                updated = True
        if updated:
            save_users(users)

# Initialize default categories
def init_categories():
    categories = load_categories()
    if not categories:
        default_categories = [
            {'id': 1, 'name': 'Technology', 'slug': 'technology', 'description': 'Latest tech trends and innovations'},
            {'id': 2, 'name': 'Business', 'slug': 'business', 'description': 'Business insights and strategies'},
            {'id': 3, 'name': 'AI & Machine Learning', 'slug': 'ai-ml', 'description': 'Artificial Intelligence and ML topics'},
            {'id': 4, 'name': 'Web Development', 'slug': 'web-dev', 'description': 'Web development tutorials and tips'},
            {'id': 5, 'name': 'Data Science', 'slug': 'data-science', 'description': 'Data analysis and visualization'},
            {'id': 6, 'name': 'Cybersecurity', 'slug': 'cybersecurity', 'description': 'Security best practices and news'}
        ]
        save_categories(default_categories)

@app.before_request
def initialize():
    if not hasattr(app, '_initialized'):
        init_admin()
        init_categories()
        app._initialized = True

@app.context_processor
def inject_user():
    return dict(current_user=get_current_user())

@app.route('/')
def index():
    # Redirect based on user type
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    elif 'user_id' in session:
        return redirect(url_for('blog'))
    else:
        return redirect(url_for('login'))

@app.route('/blog')
@user_required
def blog():
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '')
        category = request.args.get('category', '')
        tag = request.args.get('tag', '')
        sort_by = request.args.get('sort', 'newest')  # newest, oldest, popular, trending
        
        posts = load_posts()
        categories = load_categories()
        
        # Enhanced search
        if search:
            posts = search_posts(search, posts)
        
        # Filter by category
        if category:
            posts = [p for p in posts if p.get('category') == category]
        
        # Filter by tag
        if tag:
            posts = [p for p in posts if tag in p.get('tags', [])]
        
        # Add view counts and reading time to posts
        for post in posts:
            try:
                post['views'] = get_post_views(post.get('id', 0))
                post['reading_time'] = get_reading_time(post.get('content', ''))
                
                # Ensure all posts have required fields
                if 'tags' not in post:
                    post['tags'] = []
                if 'category' not in post:
                    post['category'] = ''
                if 'author_id' not in post:
                    post['author_id'] = None
            except Exception as e:
                print(f"Error processing post {post.get('id', 'unknown')}: {e}")
                # Set default values
                post['views'] = 0
                post['reading_time'] = 1
                post['tags'] = post.get('tags', [])
                post['category'] = post.get('category', '')
                post['author_id'] = post.get('author_id')
        
        # Sort posts
        if sort_by == 'oldest':
            posts.sort(key=lambda x: x.get('date', ''))
        elif sort_by == 'popular':
            posts.sort(key=lambda x: x.get('views', 0), reverse=True)
        elif sort_by == 'trending':
            # Get trending post IDs
            try:
                trending = get_trending_posts(len(posts))
                trending_ids = [p['id'] for p in trending]
                posts.sort(key=lambda x: trending_ids.index(x['id']) if x['id'] in trending_ids else len(trending_ids))
            except:
                posts.sort(key=lambda x: x.get('date', ''), reverse=True)
        else:  # newest (default)
            posts.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Pagination
        total_posts = len(posts)
        total_pages = math.ceil(total_posts / POSTS_PER_PAGE)
        start = (page - 1) * POSTS_PER_PAGE
        end = start + POSTS_PER_PAGE
        posts = posts[start:end]
        
        # Get all tags for filter
        all_posts = load_posts()
        all_tags = set()
        for post in all_posts:
            all_tags.update(post.get('tags', []))
        
        # Get trending posts for sidebar
        try:
            trending_posts = get_trending_posts(5)
            for tp in trending_posts:
                tp['views'] = get_post_views(tp.get('id', 0))
                tp['reading_time'] = get_reading_time(tp.get('content', ''))
        except Exception as e:
            print(f"Error getting trending posts: {e}")
            trending_posts = []
        
        return render_template('index.html', 
                             posts=posts, 
                             categories=categories,
                             all_tags=sorted(all_tags),
                             current_page=page,
                             total_pages=total_pages,
                             search=search,
                             selected_category=category,
                             selected_tag=tag,
                             sort_by=sort_by,
                             trending_posts=trending_posts)
    
    except Exception as e:
        print(f"Error in blog route: {e}")
        import traceback
        traceback.print_exc()
        flash(f'An error occurred: {str(e)}', 'error')
        return redirect(url_for('login'))

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    if not post:
        return "Post not found", 404
    
    # Track view
    user_id = session.get('user_id')
    track_view(post_id, user_id)
    
    # Add metadata
    post['views'] = get_post_views(post_id)
    post['reading_time'] = get_reading_time(post['content'])
    
    # Get related posts
    related_posts = get_related_posts(post, 3)
    for rp in related_posts:
        rp['views'] = get_post_views(rp['id'])
        rp['reading_time'] = get_reading_time(rp['content'])
    
    comments = load_comments()
    post_comments = [c for c in comments if c['post_id'] == post_id]
    post_comments.sort(key=lambda x: x['date'])
    
    # Add user info to comments
    users = load_users()
    for comment in post_comments:
        user = next((u for u in users if u['id'] == comment['author_id']), None)
        comment['author_name'] = user['username'] if user else 'Unknown User'
        comment['author_avatar'] = user.get('avatar', 'fas fa-user') if user else 'fas fa-user'
    
    categories = load_categories()
    category_name = next((c['name'] for c in categories if c['slug'] == post.get('category')), '')
    
    return render_template('post.html', 
                         post=post, 
                         comments=post_comments, 
                         category_name=category_name,
                         related_posts=related_posts)

@app.route('/api/posts/trending')
@user_required
def api_trending_posts():
    """API endpoint for trending posts"""
    trending = get_trending_posts(10)
    for post in trending:
        post['views'] = get_post_views(post['id'])
        post['reading_time'] = get_reading_time(post['content'])
    
    return jsonify(trending)

@app.route('/api/search')
@user_required
def api_search():
    """API endpoint for live search"""
    query = request.args.get('q', '')
    if len(query) < 2:
        return jsonify([])
    
    posts = load_posts()
    results = search_posts(query, posts)[:5]  # Limit to 5 results
    
    search_results = []
    for post in results:
        search_results.append({
            'id': post['id'],
            'title': post['title'],
            'excerpt': post['content'][:100] + '...' if len(post['content']) > 100 else post['content'],
            'category': post.get('category', ''),
            'url': url_for('post_detail', post_id=post['id'])
        })
    
    return jsonify(search_results)

@app.route('/user/dashboard')
@user_required
def user_dashboard():
    """User dashboard - blog homepage for regular users"""
    return redirect(url_for('blog'))

@app.route('/dashboard')
def dashboard_redirect():
    """Redirect to appropriate dashboard based on session"""
    if 'admin_id' in session:
        return redirect(url_for('admin_dashboard'))
    elif 'user_id' in session:
        return redirect(url_for('user_dashboard'))
    else:
        return redirect(url_for('login'))

@app.route('/profile')
@user_required
def profile():
    try:
        user = get_current_user()
        if not user:
            flash('User not found.', 'error')
            return redirect(url_for('login'))
        
        posts = load_posts()
        user_posts = [p for p in posts if p.get('author_id') == user.get('id')]
        
        # Add metadata to user posts
        for post in user_posts:
            try:
                post['views'] = get_post_views(post.get('id', 0))
                post['reading_time'] = get_reading_time(post.get('content', ''))
                
                # Ensure required fields
                if 'tags' not in post:
                    post['tags'] = []
                if 'category' not in post:
                    post['category'] = ''
            except Exception as e:
                print(f"Error processing user post {post.get('id', 'unknown')}: {e}")
                post['views'] = 0
                post['reading_time'] = 1
                post['tags'] = post.get('tags', [])
                post['category'] = post.get('category', '')
        
        user_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # User statistics
        try:
            total_views = sum(get_post_views(p.get('id', 0)) for p in user_posts)
        except:
            total_views = 0
        
        stats = {
            'total_posts': len(user_posts),
            'total_views': total_views,
            'avg_views': round(total_views / len(user_posts)) if user_posts else 0,
            'joined_date': user.get('created_at', 'Unknown')
        }
        
        return render_template('profile.html', user=user, posts=user_posts, stats=stats)
    
    except Exception as e:
        print(f"Error in profile route: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Profile error: {str(e)}', 'error')
        return redirect(url_for('blog'))

@app.route('/admin/profile')
@admin_required
def admin_profile():
    try:
        user = get_current_user()
        if not user:
            flash('Admin not found.', 'error')
            return redirect(url_for('admin_login'))
        
        posts = load_posts()
        users = load_users()
        comments = load_comments()
        
        # Admin statistics
        admin_posts = [p for p in posts if p.get('author_id') == user.get('id')]
        
        # Add metadata to admin posts
        for post in admin_posts:
            try:
                post['views'] = get_post_views(post.get('id', 0))
                post['reading_time'] = get_reading_time(post.get('content', ''))
                
                # Ensure required fields
                if 'tags' not in post:
                    post['tags'] = []
                if 'category' not in post:
                    post['category'] = ''
            except Exception as e:
                print(f"Error processing admin post {post.get('id', 'unknown')}: {e}")
                post['views'] = 0
                post['reading_time'] = 1
                post['tags'] = post.get('tags', [])
                post['category'] = post.get('category', '')
        
        admin_posts.sort(key=lambda x: x.get('date', ''), reverse=True)
        
        # Admin-specific statistics
        try:
            total_views = sum(get_post_views(p.get('id', 0)) for p in admin_posts)
        except:
            total_views = 0
        
        stats = {
            'total_posts': len(admin_posts),
            'total_views': total_views,
            'avg_views': round(total_views / len(admin_posts)) if admin_posts else 0,
            'joined_date': user.get('created_at', 'Unknown'),
            'total_users': len(users),
            'total_platform_posts': len(posts),
            'total_comments': len(comments)
        }
        
        return render_template('admin_profile.html', user=user, posts=admin_posts, stats=stats)
    
    except Exception as e:
        print(f"Error in admin profile route: {e}")
        import traceback
        traceback.print_exc()
        flash(f'Admin profile error: {str(e)}', 'error')
        return redirect(url_for('admin_dashboard'))

@app.route('/profile/edit', methods=['GET', 'POST'])
@user_required
def edit_profile():
    user = get_current_user()
    
    if request.method == 'POST':
        users = load_users()
        user_index = next(i for i, u in enumerate(users) if u['id'] == user['id'])
        
        users[user_index]['bio'] = request.form.get('bio', '')
        users[user_index]['avatar'] = request.form.get('avatar', 'fas fa-user')
        
        # Update email if changed and not taken
        new_email = request.form.get('email')
        if new_email != user['email']:
            if any(u['email'] == new_email and u['id'] != user['id'] for u in users):
                flash('Email already in use.', 'error')
                return render_template('edit_profile.html', user=user)
            users[user_index]['email'] = new_email
        
        save_users(users)
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile'))
    
    return render_template('edit_profile.html', user=user)

@app.route('/admin/profile/edit', methods=['GET', 'POST'])
@admin_required
def edit_admin_profile():
    user = get_current_user()
    
    if request.method == 'POST':
        users = load_users()
        user_index = next(i for i, u in enumerate(users) if u['id'] == user['id'])
        
        users[user_index]['bio'] = request.form.get('bio', '')
        users[user_index]['avatar'] = request.form.get('avatar', 'fas fa-user-shield')
        
        # Update email if changed and not taken
        new_email = request.form.get('email')
        if new_email != user['email']:
            if any(u['email'] == new_email and u['id'] != user['id'] for u in users):
                flash('Email already in use.', 'error')
                return render_template('admin_edit_profile.html', user=user)
            users[user_index]['email'] = new_email
        
        save_users(users)
        flash('Admin profile updated successfully!', 'success')
        return redirect(url_for('admin_profile'))
    
    return render_template('admin_edit_profile.html', user=user)

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        
        users = load_users()
        
        # Check if user exists
        if any(u['username'] == username or u['email'] == email for u in users):
            flash('Username or email already exists.', 'error')
            return render_template('register.html')
        
        new_id = max([u['id'] for u in users], default=0) + 1
        user = {
            'id': new_id,
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'is_admin': False,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        users.append(user)
        save_users(users)
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
@app.route('/login')
def login():
    return render_template('login_choice.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        user = next((u for u in users if u['username'] == username and u.get('is_admin', False)), None)
        
        if user and check_password_hash(user['password'], password):
            session['admin_id'] = user['id']
            session['user_type'] = 'admin'
            
            # Update user data structure if missing fields
            if 'bio' not in user:
                user['bio'] = 'Platform Administrator'
            if 'avatar' not in user:
                user['avatar'] = 'fas fa-user-shield'
            if 'last_login' not in user:
                user['last_login'] = None
            
            # Update last login
            user['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_users(users)
            
            flash('Admin login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid admin credentials.', 'error')
    
    return render_template('admin_login.html')

@app.route('/user/login', methods=['GET', 'POST'])
def user_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        users = load_users()
        user = next((u for u in users if u['username'] == username and not u.get('is_admin', False)), None)
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_type'] = 'user'
            
            # Update user data structure if missing fields
            if 'bio' not in user:
                user['bio'] = ''
            if 'avatar' not in user:
                user['avatar'] = 'fas fa-user'
            if 'last_login' not in user:
                user['last_login'] = None
            
            # Update last login
            user['last_login'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            save_users(users)
            
            flash('Login successful!', 'success')
            return redirect(url_for('user_dashboard'))
        else:
            flash('Invalid user credentials.', 'error')
    
    return render_template('user_login.html')

@app.route('/logout')
def logout():
    user_type = session.get('user_type', 'user')
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Admin logged out successfully.', 'info')
    return redirect(url_for('admin_login'))

@app.route('/user/logout')
def user_logout():
    session.clear()
    flash('Logged out successfully.', 'info')
    return redirect(url_for('user_login'))

@app.route('/new', methods=['GET', 'POST'])
@login_required
def new_post():
    if request.method == 'POST':
        posts = load_posts()
        new_id = max([p['id'] for p in posts], default=0) + 1
        
        tags = [tag.strip() for tag in request.form['tags'].split(',') if tag.strip()]
        
        # Get the current user ID (works for both admin and user sessions)
        current_user = get_current_user()
        if not current_user:
            flash('Session expired. Please log in again.', 'error')
            return redirect(url_for('login'))
        
        post = {
            'id': new_id,
            'title': request.form['title'],
            'content': request.form['content'],
            'category': request.form['category'],
            'tags': tags,
            'author_id': current_user['id'],
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'updated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        posts.append(post)
        save_posts(posts)
        flash('Post created successfully!', 'success')
        return redirect(url_for('post_detail', post_id=new_id))
    
    categories = load_categories()
    return render_template('new_post.html', categories=categories)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
@login_required
def edit_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('blog'))
    
    current_user = get_current_user()
    # Handle posts created before user system (no author_id)
    post_author_id = post.get('author_id')
    if post_author_id and post_author_id != current_user['id'] and not current_user.get('is_admin', False):
        flash('You can only edit your own posts.', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    if request.method == 'POST':
        post['title'] = request.form['title']
        post['content'] = request.form['content']
        post['category'] = request.form['category']
        post['tags'] = [tag.strip() for tag in request.form['tags'].split(',') if tag.strip()]
        post['updated_at'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        save_posts(posts)
        flash('Post updated successfully!', 'success')
        return redirect(url_for('post_detail', post_id=post_id))
    
    categories = load_categories()
    return render_template('edit_post.html', post=post, categories=categories)

@app.route('/delete/<int:post_id>')
@login_required
def delete_post(post_id):
    posts = load_posts()
    post = next((p for p in posts if p['id'] == post_id), None)
    
    if not post:
        flash('Post not found.', 'error')
        return redirect(url_for('blog'))
    
    current_user = get_current_user()
    # Handle posts created before user system (no author_id)
    post_author_id = post.get('author_id')
    if post_author_id and post_author_id != current_user['id'] and not current_user.get('is_admin', False):
        flash('You can only delete your own posts.', 'error')
        return redirect(url_for('post_detail', post_id=post_id))
    
    posts.remove(post)
    save_posts(posts)
    
    # Delete associated comments
    comments = load_comments()
    comments = [c for c in comments if c['post_id'] != post_id]
    save_comments(comments)
    
    flash('Post deleted successfully!', 'success')
    return redirect(url_for('blog'))

@app.route('/comment/<int:post_id>', methods=['POST'])
@login_required
def add_comment(post_id):
    content = request.form['content']
    
    # Get the current user ID (works for both admin and user sessions)
    current_user = get_current_user()
    if not current_user:
        flash('Session expired. Please log in again.', 'error')
        return redirect(url_for('login'))
    
    comments = load_comments()
    new_id = max([c['id'] for c in comments], default=0) + 1
    
    comment = {
        'id': new_id,
        'post_id': post_id,
        'author_id': current_user['id'],
        'content': content,
        'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    comments.append(comment)
    save_comments(comments)
    
    flash('Comment added successfully!', 'success')
    return redirect(url_for('post_detail', post_id=post_id))

@app.route('/admin')
@admin_required
def admin_dashboard():
    posts = load_posts()
    users = load_users()
    comments = load_comments()
    categories = load_categories()
    
    stats = {
        'total_posts': len(posts),
        'total_users': len(users),
        'total_comments': len(comments),
        'total_categories': len(categories)
    }
    
    recent_posts = sorted(posts, key=lambda x: x['date'], reverse=True)[:5]
    recent_comments = sorted(comments, key=lambda x: x['date'], reverse=True)[:5]
    
    return render_template('admin/dashboard.html', 
                         stats=stats, 
                         recent_posts=recent_posts, 
                         recent_comments=recent_comments)

@app.route('/admin/users')
@admin_required
def admin_users():
    users = load_users()
    return render_template('admin/users.html', users=users)

@app.route('/admin/posts')
@admin_required
def admin_posts():
    posts = load_posts()
    users = load_users()
    
    # Add author names to posts
    for post in posts:
        if post.get('author_id'):
            author = next((u for u in users if u['id'] == post['author_id']), None)
            post['author_name'] = author['username'] if author else 'Unknown User'
        else:
            post['author_name'] = 'Legacy Post'
    
    posts.sort(key=lambda x: x['date'], reverse=True)
    return render_template('admin/posts.html', posts=posts)

@app.route('/admin/categories', methods=['GET', 'POST'])
@admin_required
def admin_categories():
    if request.method == 'POST':
        categories = load_categories()
        new_id = max([c['id'] for c in categories], default=0) + 1
        
        category = {
            'id': new_id,
            'name': request.form['name'],
            'slug': request.form['name'].lower().replace(' ', '-')
        }
        
        categories.append(category)
        save_categories(categories)
        flash('Category added successfully!', 'success')
    
    categories = load_categories()
    return render_template('admin/categories.html', categories=categories)

@app.route('/admin/delete_category/<int:category_id>')
@admin_required
def delete_category(category_id):
    categories = load_categories()
    categories = [c for c in categories if c['id'] != category_id]
    save_categories(categories)
    flash('Category deleted successfully!', 'success')
    return redirect(url_for('admin_categories'))

if __name__ == '__main__':
    app.run(debug=True)