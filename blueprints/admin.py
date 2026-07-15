from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from models import User, Property, Testimonial, BlogPost, ContactMessage, Staff
from extensions import db
import os
import json
import re

from forms.admin_forms import SocialMediaPostForm
from utils.meta_api import post_to_facebook, post_to_instagram

admin_bp = Blueprint('admin', __name__)

def slugify(title):
    slug = re.sub(r'[^\w\s-]', '', title).lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

from forms.auth_forms import LoginForm

@admin_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated and current_user.is_admin_user():
        return redirect(url_for('admin.dashboard'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data) and user.is_admin_user():
            login_user(user, remember=form.remember.data)
            flash('Welcome back, Admin!', 'success')
            print('Welcome back, Admin!') 
            return redirect(url_for('admin.dashboard'))
        flash('Invalid credentials or you do not have admin access.', 'danger')
    return render_template('admin/login.html', form=form)

@admin_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('admin.login'))

@admin_bp.route('/')
@login_required
def dashboard():
    property_count = Property.query.count()
    message_count = ContactMessage.query.filter_by(is_read=False).count()
    blog_count = BlogPost.query.count()
    staff_count = Staff.query.count()
    return render_template('admin/dashboard.html', 
                           property_count=property_count,
                           message_count=message_count,
                           blog_count=blog_count,
                           staff_count=staff_count)

# Property Management
@admin_bp.route('/properties')
@login_required
def properties():
    return redirect(url_for('property_mgmt.property_list'))

@admin_bp.route('/property/add', methods=['GET', 'POST'])
@login_required
def add_property():
    return redirect(url_for('property_mgmt.add_property'))
    if request.method == 'POST':
        title = request.form.get('title')
        property_type = request.form.get('property_type')
        description = request.form.get('description')
        price = request.form.get('price')
        location = request.form.get('location')
        land_area_sqm = request.form.get('land_area_sqm')
        bedrooms = request.form.get('bedrooms')
        bathrooms = request.form.get('bathrooms')
        featured = request.form.get('featured') == 'on'
        status = request.form.get('status')
        
        # Handle image uploads
        images = []
        files = request.files.getlist('images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                # Add timestamp to avoid collisions
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{os.urandom(4).hex()}{ext}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                images.append(filename)
        
        slug = slugify(title)
        # Ensure unique slug
        while Property.query.filter_by(slug=slug).first():
            slug = f"{slug}-{os.urandom(2).hex()}"
        
        prop = Property(
            title=title,
            slug=slug,
            property_type=property_type,
            description=description,
            price=price,
            location=location,
            land_area_sqm=land_area_sqm or None,
            bedrooms=int(bedrooms) if bedrooms else None,
            bathrooms=int(bathrooms) if bathrooms else None,
            featured=featured,
            status=status,
            images=images
        )
        db.session.add(prop)
        db.session.commit()
        flash('Property added successfully')
        return redirect(url_for('admin.properties'))
    return render_template('admin/property_form.html', property=None)

@admin_bp.route('/property/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_property(id):
    prop = Property.query.get_or_404(id)
    if request.method == 'POST':
        prop.title = request.form.get('title')
        prop.property_type = request.form.get('property_type')
        prop.description = request.form.get('description')
        prop.price = request.form.get('price')
        prop.location = request.form.get('location')
        prop.land_area_sqm = request.form.get('land_area_sqm') or None
        prop.bedrooms = int(request.form.get('bedrooms')) if request.form.get('bedrooms') else None
        prop.bathrooms = int(request.form.get('bathrooms')) if request.form.get('bathrooms') else None
        prop.featured = request.form.get('featured') == 'on'
        prop.status = request.form.get('status')
        
        # Handle new images
        files = request.files.getlist('images')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                name, ext = os.path.splitext(filename)
                filename = f"{name}_{os.urandom(4).hex()}{ext}"
                file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
                current_images = prop.images or []
                current_images.append(filename)
                prop.images = current_images
        
        # Delete images
        delete_images = request.form.getlist('delete_images')
        if delete_images:
            current_images = prop.images or []
            for img in delete_images:
                if img in current_images:
                    # Delete file from disk
                    img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img)
                    if os.path.exists(img_path):
                        os.remove(img_path)
                    current_images.remove(img)
            prop.images = current_images
        
        db.session.commit()
        flash('Property updated')
        return redirect(url_for('admin.properties'))
    return render_template('admin/property_form.html', property=prop)

@admin_bp.route('/property/delete/<string:id>')
@login_required
def delete_property(id):
    prop = Property.query.get_or_404(id)
    # Delete image files
    if prop.images:
        for img in prop.images:
            img_path = os.path.join(current_app.config['UPLOAD_FOLDER'], img)
            if os.path.exists(img_path):
                os.remove(img_path)
    db.session.delete(prop)
    db.session.commit()
    flash('Property deleted')
    return redirect(url_for('admin.properties'))

# Testimonials
@admin_bp.route('/testimonials')
@login_required
def testimonials():
    testimonial_list = Testimonial.query.order_by(db.desc(Testimonial.created_at)).all()
    return render_template('admin/testimonials.html', testimonials=testimonial_list)

@admin_bp.route('/testimonial/add', methods=['POST'])
@login_required
def add_testimonial():
    name = request.form.get('name')
    role = request.form.get('role')
    content = request.form.get('content')
    rating = int(request.form.get('rating'))
    is_published = request.form.get('is_published') == 'on'
    
    testimonial = Testimonial(client_name=name, client_role=role, content=content, rating=rating, is_published=is_published)
    db.session.add(testimonial)
    db.session.commit()
    flash('Testimonial added')
    return redirect(url_for('admin.testimonials'))

@admin_bp.route('/testimonial/delete/<string:id>')
@login_required
def delete_testimonial(id):
    testimonial = Testimonial.query.get_or_404(id)
    db.session.delete(testimonial)
    db.session.commit()
    flash('Testimonial deleted')
    return redirect(url_for('admin.testimonials'))

# Blog Management
@admin_bp.route('/blog')
@login_required
def blog_posts():
    posts = BlogPost.query.order_by(db.desc(BlogPost.created_at)).all()
    return render_template('admin/blog.html', posts=posts)

@admin_bp.route('/blog/add', methods=['GET', 'POST'])
@login_required
def add_blog():
    if request.method == 'POST':
        title = request.form.get('title')
        excerpt = request.form.get('excerpt')
        content = request.form.get('content')
        author = request.form.get('author')
        is_published = request.form.get('is_published') == 'on'
        
        # Handle image upload
        image_file = request.files.get('image')
        image_filename = None
        if image_file and allowed_file(image_file.filename):
            filename = secure_filename(image_file.filename)
            name, ext = os.path.splitext(filename)
            image_filename = f"blog_{name}_{os.urandom(4).hex()}{ext}"
            image_file.save(os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], image_filename))
        
        slug = slugify(title)
        while BlogPost.query.filter_by(slug=slug).first():
            slug = f"{slug}-{os.urandom(2).hex()}"
        
        post = BlogPost(title=title, slug=slug, excerpt=excerpt, content=content, author=author, image=image_filename, is_published=is_published)
        db.session.add(post)
        db.session.commit()
        flash('Blog post added')
        return redirect(url_for('admin.blog_posts'))
    return render_template('admin/blog_form.html', post=None)

@admin_bp.route('/blog/edit/<string:id>', methods=['GET', 'POST'])
@login_required
def edit_blog(id):
    post = BlogPost.query.get_or_404(id)
    if request.method == 'POST':
        post.title = request.form.get('title')
        post.excerpt = request.form.get('excerpt')
        post.content = request.form.get('content')
        post.author = request.form.get('author')
        post.is_published = request.form.get('is_published') == 'on'
        
        image_file = request.files.get('image')
        if image_file and allowed_file(image_file.filename):
            # Delete old image
            if post.image:
                old_path = os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], post.image)
                if os.path.exists(old_path):
                    os.remove(old_path)
            filename = secure_filename(image_file.filename)
            name, ext = os.path.splitext(filename)
            post.image = f"blog_{name}_{os.urandom(4).hex()}{ext}"
            image_file.save(os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], post.image))
        
        db.session.commit()
        flash('Blog post updated')
        return redirect(url_for('admin.blog_posts'))
    return render_template('admin/blog_form.html', post=post)

@admin_bp.route('/blog/delete/<string:id>')
@login_required
def delete_blog(id):
    post = BlogPost.query.get_or_404(id)
    if post.image:
        img_path = os.path.join(current_app.config['BLOG_UPLOAD_FOLDER'], post.image)
        if os.path.exists(img_path):
            os.remove(img_path)
    db.session.delete(post)
    db.session.commit()
    flash('Blog post deleted')
    return redirect(url_for('admin.blog_posts'))

# Messages
@admin_bp.route('/messages')
@login_required
def messages():
    msgs = ContactMessage.query.order_by(db.desc(ContactMessage.created_at)).all()
    return render_template('admin/messages.html', messages=msgs)

@admin_bp.route('/message/mark-read/<string:id>')
@login_required
def mark_read(id):
    msg = ContactMessage.query.get_or_404(id)
    msg.is_read = True
    db.session.commit()
    return redirect(url_for('admin.messages'))



















@admin_bp.route('/media', methods=['GET'])
@login_required
def media_dashboard():
    form = SocialMediaPostForm()
    return render_template('admin/media.html', form=form)

@admin_bp.route('/media/post', methods=['POST'])
@login_required
def post_social_media():
    form = SocialMediaPostForm()
    if form.validate_on_submit():
        message = form.message.data
        platforms = form.platforms.data
        image = form.image.data
        video = form.video.data
        
        # Save uploaded files temporarily
        image_path = None
        video_path = None
        if image:
            filename = secure_filename(image.filename)
            image_path = os.path.join('/tmp', filename)
            image.save(image_path)
        if video:
            filename = secure_filename(video.filename)
            video_path = os.path.join('/tmp', filename)
            video.save(video_path)
        
        results = {}
        try:
            if 'facebook' in platforms:
                resp = post_to_facebook(
                    current_app.config['META_PAGE_ID'],
                    message,
                    image_path,
                    video_path
                )
                results['facebook'] = resp
            if 'instagram' in platforms:
                # For Instagram we need public URLs – we'll pass the file path as a placeholder.
                # In production, you'd upload to S3 and provide the URL.
                # We'll simulate by passing a temporary URL (not supported)
                resp = post_to_instagram(
                    current_app.config['META_INSTAGRAM_BUSINESS_ID'],
                    message,
                    image_path,  # should be URL
                    video_path   # should be URL
                )
                results['instagram'] = resp
        except Exception as e:
            flash(f'Error posting: {str(e)}', 'danger')
        finally:
            # Clean up temp files
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            if video_path and os.path.exists(video_path):
                os.remove(video_path)
        
        # Parse results for feedback
        if 'facebook' in results and 'id' in results.get('facebook', {}):
            flash('Posted to Facebook successfully.', 'success')
        elif 'facebook' in results:
            flash(f'Facebook error: {results["facebook"].get("error", {}).get("message", "Unknown error")}', 'danger')
        
        if 'instagram' in results and 'id' in results.get('instagram', {}):
            flash('Posted to Instagram successfully.', 'success')
        elif 'instagram' in results:
            flash(f'Instagram error: {results["instagram"].get("error", {}).get("message", "Unknown error")}', 'danger')
        
        return redirect(url_for('admin.media_dashboard'))
    
    # If form invalid, re-render with errors
    return render_template('admin/media.html', form=form)

