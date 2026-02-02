# Fix for "Publish Article Page Not Found" Error

## Issues Identified and Fixed

### 1. Session Handling in new_post Route
**Problem**: The `new_post` function was trying to access `session['user_id']` but when an admin is logged in, they have `session['admin_id']` instead.

**Fix**: Updated the function to use `get_current_user()` which works for both admin and user sessions:
```python
# Before (caused error for admins)
'author_id': session['user_id']

# After (works for both admin and user)
current_user = get_current_user()
'author_id': current_user['id']
```

### 2. Index Route Redirect Logic
**Problem**: The index route only checked for `'user_id'` in session, causing admins to be redirected to login even when already authenticated.

**Fix**: Updated to handle both admin and user sessions:
```python
# Before
if 'user_id' not in session:
    return redirect(url_for('login'))
return redirect(url_for('blog'))

# After
if 'admin_id' in session:
    return redirect(url_for('admin_dashboard'))
elif 'user_id' in session:
    return redirect(url_for('blog'))
else:
    return redirect(url_for('login'))
```

### 3. Route Decorator Changes
**Changed**: Updated `new_post` route from `@user_required` to `@login_required` to allow both admins and users to create posts.

### 4. Comment Function Fix
**Fixed**: Same session handling issue in `add_comment` function - now uses `get_current_user()` instead of direct session access.

## Testing the Fix

### For User Login:
1. Go to `http://127.0.0.1:5000/`
2. Choose "User Login"
3. Login with user credentials (e.g., hari/password)
4. Click "Write" in navigation or "New Article" in profile
5. Should now successfully access the publish article page

### For Admin Login:
1. Go to `http://127.0.0.1:5000/`
2. Choose "Administrator Login"
3. Login with admin credentials (admin/admin123)
4. Click "Write" in navigation
5. Should also successfully access the publish article page

## Root Cause
The error was caused by inconsistent session handling between admin and user logins. The application was trying to access user-specific session keys even when an admin was logged in, causing the routes to fail and return "page not found" errors.

## Resolution Status
✅ **FIXED** - Both admin and user logins can now successfully access the "Publish Article" page without errors.