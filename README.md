Link:https://blog-application-3-h22k.onrender.com/admin/login
# Advanced Blog Application

A comprehensive blog application built with Python Flask, HTML, and CSS featuring user authentication, admin dashboard, and advanced blog management.

## Features

### User Management
- User registration and login system
- Session-based authentication
- Admin and regular user roles
- Secure password hashing

### Blog Management
- Create, edit, and delete blog posts
- Categories and tags system
- Rich post metadata (creation/update dates)
- Author attribution

### Advanced Features
- **Search & Filter**: Search posts by title/content, filter by category or tags
- **Pagination**: Efficient pagination for large numbers of posts
- **Comments System**: Users can comment on posts
- **Admin Dashboard**: Complete admin interface for managing users, posts, and categories
- **Responsive Design**: Mobile-friendly interface

### Admin Features
- Dashboard with statistics
- User management
- Post management (edit/delete any post)
- Category management
- View all comments

## Setup

1. Install Python dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run the application:
   ```
   python app.py
   ```

3. Open your browser and go to `http://localhost:5000`

## Default Admin Account

- **Username**: admin
- **Password**: admin123

## Usage

### For Regular Users
- **Register/Login**: Create an account or login
- **Browse Posts**: View all posts with search and filter options
- **Read Posts**: Click on any post to read full content
- **Create Posts**: Write new blog posts with categories and tags
- **Comment**: Add comments to posts
- **Manage Own Posts**: Edit or delete your own posts

### For Admins
- **Admin Dashboard**: Access via "Admin" button after login
- **Manage Users**: View all registered users
- **Manage Posts**: Edit or delete any post
- **Manage Categories**: Add or remove post categories
- **View Statistics**: See total counts of posts, users, comments

## File Structure

```
blog-app/
├── app.py                    # Main Flask application
├── requirements.txt          # Python dependencies
├── users.json               # User accounts storage
├── posts.json               # Blog posts storage
├── comments.json            # Comments storage
├── categories.json          # Categories storage
├── templates/               # HTML templates
│   ├── base.html           # Base template with navigation
│   ├── index.html          # Homepage with search/filter
│   ├── post.html           # Individual post view with comments
│   ├── new_post.html       # Create new post form
│   ├── edit_post.html      # Edit post form
│   ├── login.html          # Login form
│   ├── register.html       # Registration form
│   └── admin/              # Admin templates
│       ├── dashboard.html  # Admin dashboard
│       ├── users.html      # User management
│       ├── posts.html      # Post management
│       └── categories.html # Category management
└── static/
    └── style.css           # Complete responsive CSS
```

## Technologies Used

- **Backend**: Python with Flask framework
- **Authentication**: Werkzeug password hashing, Flask sessions
- **Frontend**: HTML5, CSS3 with Font Awesome icons
- **Storage**: JSON file-based storage
- **Styling**: Custom responsive CSS with modern design

## Key Features Implemented

✅ User registration & login  
✅ Create/edit/delete posts  
✅ Categories & tags  
✅ Comment system  
✅ Admin dashboard  
✅ Search posts  
✅ Pagination  
✅ Responsive design  
✅ Flash messaging  
✅ Role-based access control  
✅ Post filtering  
✅ User management  
✅ Category management
