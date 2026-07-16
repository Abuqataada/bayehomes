from flask import Blueprint, request, jsonify, render_template, current_app
from flask_login import login_required, current_user
from models import VisitorFeedback, db
from forms.feedback_forms import VisitorFeedbackForm
from utils.geo import get_visitor_location
from datetime import datetime

feedback_bp = Blueprint('feedback', __name__, url_prefix='/feedback')

@feedback_bp.route('/submit', methods=['POST'])
def submit_feedback():
    """Submit feedback from a visitor."""
    form = VisitorFeedbackForm()
    
    if form.validate_on_submit():
        # Get visitor IP
        ip_address = request.headers.get('X-Forwarded-For', request.remote_addr).split(',')[0].strip()
        
        # Get location data
        location = get_visitor_location(ip_address)
        
        # Create feedback entry
        feedback = VisitorFeedback(
            name=form.name.data.strip(),
            email=form.email.data.strip() if form.email.data else None,
            message=form.message.data.strip(),
            rating=form.rating.data or 5,
            ip_address=ip_address,
            city=location.get('city'),
            region=location.get('region'),
            country=location.get('country'),
            country_code=location.get('country_code'),
            latitude=location.get('latitude'),
            longitude=location.get('longitude'),
            user_timezone=location.get('timezone'),
            isp=location.get('isp'),
            page_url=form.page_url.data,
            page_title=form.page_title.data
        )
        
        db.session.add(feedback)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Thank you for your feedback!'
        }), 201
    
    return jsonify({
        'success': False,
        'errors': form.errors
    }), 400

@feedback_bp.route('/')
@login_required
def list_feedback():
    """Admin view - list all feedback entries."""
    if not current_user.is_admin_user():
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Get filter parameters
    status = request.args.get('status', 'all')  # all, unread, resolved
    search = request.args.get('search', '')
    
    query = VisitorFeedback.query
    
    # Apply filters
    if status == 'unread':
        query = query.filter_by(is_read=False)
    elif status == 'resolved':
        query = query.filter_by(is_resolved=True)
    
    if search:
        query = query.filter(
            VisitorFeedback.name.contains(search) |
            VisitorFeedback.message.contains(search) |
            VisitorFeedback.email.contains(search)
        )
    
    feedbacks = query.order_by(VisitorFeedback.created_at.desc()).all()
    
    return render_template('admin/feedback_list.html', feedbacks=feedbacks, status=status, search=search)

@feedback_bp.route('/<feedback_id>/read', methods=['POST'])
@login_required
def mark_read(feedback_id):
    """Mark feedback as read."""
    if not current_user.is_admin_user():
        return jsonify({'error': 'Unauthorized'}), 403
    
    feedback = VisitorFeedback.query.get_or_404(feedback_id)
    feedback.is_read = True
    feedback.updated_at = datetime.now()
    db.session.commit()
    
    return jsonify({'success': True})

@feedback_bp.route('/<feedback_id>/resolve', methods=['POST'])
@login_required
def mark_resolved(feedback_id):
    """Mark feedback as resolved."""
    if not current_user.is_admin_user():
        return jsonify({'error': 'Unauthorized'}), 403
    
    feedback = VisitorFeedback.query.get_or_404(feedback_id)
    feedback.is_resolved = True
    feedback.is_read = True
    feedback.updated_at = datetime.now()
    db.session.commit()
    
    return jsonify({'success': True})

@feedback_bp.route('/<feedback_id>', methods=['DELETE'])
@login_required
def delete_feedback(feedback_id):
    """Delete feedback entry."""
    if not current_user.is_admin_user():
        return jsonify({'error': 'Unauthorized'}), 403
    
    feedback = VisitorFeedback.query.get_or_404(feedback_id)
    db.session.delete(feedback)
    db.session.commit()
    
    return jsonify({'success': True})

@feedback_bp.route('/count')
@login_required
def unread_count():
    """Get count of unread feedback (for dashboard badge)."""
    if not current_user.is_admin_user():
        return jsonify({'error': 'Unauthorized'}), 403
    
    count = VisitorFeedback.query.filter_by(is_read=False).count()
    return jsonify({'unread_count': count})

