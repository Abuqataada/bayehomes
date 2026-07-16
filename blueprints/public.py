from flask import Blueprint, render_template, request, jsonify, current_app
from models import Property, Testimonial, BlogPost, ContactMessage, VisitorFeedback
from extensions import db
from sqlalchemy import or_
import re
import random

public_bp = Blueprint('public', __name__)

def slugify(title):
    slug = re.sub(r'[^\w\s-]', '', title).lower()
    slug = re.sub(r'[-\s]+', '-', slug)
    return slug

@public_bp.route('/')
def home():
    featured_properties = Property.query.filter_by(featured=True, status='available').limit(6).all()
    testimonials = Testimonial.query.filter_by(is_published=True).order_by(db.desc(Testimonial.created_at)).limit(4).all()
    recent_posts = BlogPost.query.filter_by(is_published=True).order_by(db.desc(BlogPost.created_at)).limit(3).all()
    # Fetch latest feedback with rating >= 4 and a non-empty message
    testimonials = VisitorFeedback.query.filter(
        VisitorFeedback.rating >= 4,
        VisitorFeedback.message.isnot(None),
        VisitorFeedback.message != ''
    ).order_by(VisitorFeedback.created_at.desc()).limit(10).all()
    
    return render_template('index.html', 
                           featured_properties=featured_properties,
                           testimonials=testimonials,
                           recent_posts=recent_posts,
                           meta_description='Baye Homes offers verified land and building options in Abuja with flexible payment plans, secure documentation, and investment advisory services.'
                           )

@public_bp.route('/about')
def about():
    return render_template('about.html')

# Example route in your Flask app (e.g., routes/investment.py or similar)
from flask import render_template

@public_bp.route('/investment-options')
def investment_options():
    search = request.args.get('search', '').strip()
    property_type = request.args.get('type', '').strip()
    location = request.args.get('location', '').strip()

    query = Property.query.filter_by(status='available')
    if search:
        term = f"%{search}%"
        query = query.filter(or_(
            Property.title.ilike(term),
            Property.estate.ilike(term),
            Property.location.ilike(term),
            Property.city.ilike(term),
            Property.description.ilike(term)
        ))
    if property_type in ['land', 'building']:
        query = query.filter_by(property_type=property_type)
    if location:
        query = query.filter(Property.location.ilike(f"%{location}%"))

    investment_properties = query.order_by(db.desc(Property.featured), db.desc(Property.created_at)).all()
    locations = [row[0] for row in db.session.query(Property.location).filter(Property.location.isnot(None)).distinct().all()]
    return render_template(
        'investment-options.html',
        investment_properties=investment_properties,
        locations=locations,
        search=search,
        property_type=property_type,
        location=location,
        meta_description='Search Baye Homes investment properties, land, and buildings in Abuja with verified documents and flexible payment options.'
    )

@public_bp.route('/chatbot', methods=['POST'])
def chatbot():
    payload = request.get_json(silent=True) or {}
    question = (payload.get('message') or '').strip().lower()
    if not question:
        return jsonify({'reply': 'Type your question (e.g., “payment plan”, “documents”, “prices”, or a location) and I’ll help.'})

    # Professional greeting handling
    greeting_q = re.sub(r'\s+', ' ', question).strip()
    greetings = [
        'hi', 'hello', 'hey', 'good morning', 'good afternoon', 'good evening',
        'good day', 'welcome', 'howdy', 'greetings'
    ]
    if any(g in greeting_q for g in greetings) or greeting_q in greetings:
        greeting_replies = [
            "Hello and welcome to Baye Homes. How may I assist you today—prices, payment plans, available locations, or property documents?",
            "Good day. Thank you for contacting Baye Homes. Would you like help with land/building options, installment plans, or documentation requirements?",
            "Hi there—welcome to Baye Homes. Kindly tell me what you're looking for (location, budget, or payment plan) and I’ll guide you accordingly."
        ]
        return jsonify({'reply': random.choice(greeting_replies)})

    # Normalize common user phrases
    q = question
    q = re.sub(r'\s+', ' ', q).strip()

    # "About company" intent (high priority)
    about_company_triggers = [
        'who are you', 'what are you', 'what is this', 'what is bay', 'what is bayehomes',
        'what do you do', 'about bayehomes', 'about us', 'company', 'services', 'service',
        'who is bayehomes', 'tell me about bayehomes', 'mission', 'vision'
    ]
    if any(t in q for t in about_company_triggers) or q.startswith('who'):
        about_replies = [
            "Baye Homes is a trusted real estate company in Abuja focused on verified land and building options, secure documentation guidance, and investment advisory. We help clients buy with clarity—property details, availability, and payment plans—so you can make informed decisions.",
            "Welcome. Baye Homes provides landed property and building opportunities in Abuja, along with consultancy support for documentation and flexible payment plans. Our goal is to connect clients with verified options and help them complete the process confidently.",
            "Baye Homes supports you end-to-end: finding suitable available properties, explaining payment plans, and guiding documentation requirements for land/building purchases and investments."
        ]
        return jsonify({'reply': random.choice(about_replies)})

    # Intent detection with simple regexes + keyword sets
    def has_any(tokens):
        return any(t in q for t in tokens)

    intents = []

    # Pricing / availability
    if has_any(['price', 'cost', 'available', 'available?', 'availability', 'how much', 'price range', 'rent', 'buy', 'buying']):
        intents.append('pricing')

    # Payment plans / installment
    if has_any(['installment', 'pay', 'payment plan', 'deposit', 'initial deposit', 'balance', '4 months', 'monthly']):
        intents.append('payment_plan')

    # Documents
    if has_any(['document', 'documents', 'deed', 'survey', 'permit', 'building plan', 'allocation', 'receipt']):
        intents.append('documents')

    # Locations
    if has_any(['location', 'where', 'kije', 'kuje', 'lugbe', 'idu', 'katampe', 'guzape', 'guzape', 'wuse', 'gwarinpa', 'abaji', 'fct']):
        intents.append('locations')

    # Safety / verification
    if has_any(['safe', 'verified', 'verification', 'confirm', 'check', 'boundary', 'boundary risk', 'fraud', 'encroachment']):
        intents.append('verification')

    # Contact / office
    if has_any(['contact', 'call', 'phone', 'whatsapp', 'email', 'office', 'address', 'where is your office']):
        intents.append('contact')

    # Investment
    if has_any(['investment', 'invest', 'roi', 'return', 'appreciation', 'long term']):
        intents.append('investment')

    # Staff/admin info
    if has_any(['staff', 'admin', 'dashboard', 'rating', 'reports']):
        intents.append('staffing')

    # If no intent detected, fall back to generic knowledge search
    if not intents:
        # Keyword fallbacks
        if has_any(['installment']):
            intents = ['payment_plan']
        elif has_any(['documents', 'deed', 'permit', 'survey', 'allocation']):
            intents = ['documents']
        elif has_any(['location', 'kuje', 'lugbe', 'katampe', 'guzape', 'idu']):
            intents = ['locations']
        elif has_any(['contact', 'whatsapp', 'phone', 'email']):
            intents = ['contact']
        elif has_any(['investment']):
            intents = ['investment']
        elif has_any(['safe', 'verified']):
            intents = ['verification']
        else:
            intents = ['general']

    # Diverse, randomized responses per intent
    payment_plan_replies = [
        "Yes—Baye Homes offers flexible payment plans. A common structure is 40% initial deposit, then the balance is spread over about 4 months (depending on the property).",
        "We support installment payments. Many clients start with a deposit (often around 40%) and complete payment over 4 months based on the property you choose.",
        "Payment plans are available. Tell me the property type and preferred location, and I’ll help you understand a suitable plan."
    ]
    documents_replies = [
        "After full payment, clients typically receive documents such as Deed of Assignment, Building Plan/Permit, Certificate of Allocation, and Provisional Survey Plan (where applicable).",
        "Once payment is completed, we guide you through the documentation process—Deed of Assignment, Building Permit/Plan, Certificate of Allocation, and related survey documents.",
        "We can walk you through the full document set based on the property. Are you looking for land or building?"
    ]
    locations_replies = [
        "Baye Homes focuses on key Abuja areas including Kuje, Lugbe, Idu, Katampe, Guzape, and other growing districts.",
        "We have options across Abuja. Share your preferred location (e.g., Katampe, Kuje, Lugbe, or Guzape) and I’ll suggest available properties.",
        "Tell me the estate/location you prefer and your budget, and I’ll recommend matching available options."
    ]
    contact_replies = [
        "You can reach Baye Homes on +234 812 846 6760 or email contact@bayehomes.com. WhatsApp is welcome too.",
        "For fastest support: WhatsApp +234 812 846 6760. You can also email contact@bayehomes.com.",
        "Need a quick reply? Send us a WhatsApp message at +234 812 846 6760 and our team will respond."
    ]
    verification_replies = [
        "We verify property documentation and boundaries before listing options to reduce ownership and encroachment risk.",
        "Yes—our listings are based on verified documentation and boundary checks to help protect buyers.",
        "Baye Homes prioritizes verification: docs + boundary checks before properties are made available."
    ]
    investment_replies = [
        "We offer land and building investment opportunities in Abuja with verified documents and long-term appreciation potential.",
        "Investment options are available—tell me your target budget and time horizon (short/long term) and I’ll suggest suitable properties.",
        "If you’re investing, share your preferred location and budget so we can recommend options with strong long-term value."
    ]
    staff_replies = [
        "Staff accounts, property allocation, daily reporting, ratings, chat, and notifications are handled on the admin dashboard.",
        "Staff tools include reporting, ratings, chat, and notifications—managed by admins through the dashboard."
    ]
    general_replies = [
        "I can help with payment plans, available prices, documentation, or suitable locations. What would you like to know?",
        "Ask me about installment payments, property documents, or available options (prices + locations).",
        "Tell me your request (price, location, documents, or payment plan) and I’ll guide you."
    ]

    # Choose the highest-priority intent if multiple matched
    priority = ['pricing', 'payment_plan', 'documents', 'locations', 'verification', 'contact', 'investment', 'staffing', 'general']
    selected = None
    for p in priority:
        if p in intents:
            selected = p
            break
    if not selected:
        selected = intents[0]

    if selected == 'pricing':
        props = Property.query.filter_by(status='available').order_by(db.desc(Property.created_at)).limit(3).all()
        if props:
            lines = [f"{p.title} ({p.location}) — ₦{float(p.price):,.0f}" for p in props]
            return jsonify({
                'reply': "Here are a few available options right now: " + "; ".join(lines) +
                         ". If you tell me your preferred location and budget, I’ll narrow it down."
            })
        return jsonify({'reply': "Right now, I'm not seeing available listings. Please contact us on WhatsApp +234 812 846 6760 and our team will assist you with the latest options."})

    if selected == 'payment_plan':
        return jsonify({'reply': random.choice(payment_plan_replies)})

    if selected == 'documents':
        return jsonify({'reply': random.choice(documents_replies)})

    if selected == 'locations':
        return jsonify({'reply': random.choice(locations_replies)})

    if selected == 'verification':
        return jsonify({'reply': random.choice(verification_replies)})

    if selected == 'contact':
        return jsonify({'reply': random.choice(contact_replies)})

    if selected == 'investment':
        return jsonify({'reply': random.choice(investment_replies)})

    if selected == 'staffing':
        return jsonify({'reply': random.choice(staff_replies)})

    return jsonify({'reply': random.choice(general_replies)})

@public_bp.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')
        
        contact = ContactMessage(name=name, email=email, phone=phone, message=message)
        db.session.add(contact)
        db.session.commit()
        return render_template('contact.html', success=True)
    return render_template('contact.html')

@public_bp.route('/properties')
def properties():
    page = request.args.get('page', 1, type=int)
    per_page = 9
    
    query = Property.query.filter_by(status='available')
    
    # Search
    search = request.args.get('search', '')
    if search:
        query = query.filter(Property.title.contains(search) | Property.location.contains(search))
    
    # Filters
    property_type = request.args.get('type', '')
    if property_type in ['land', 'building']:
        query = query.filter_by(property_type=property_type)
    
    location = request.args.get('location', '')
    if location:
        query = query.filter(Property.location.contains(location))
    
    min_price = request.args.get('min_price', type=float)
    if min_price:
        query = query.filter(Property.price >= min_price)
    max_price = request.args.get('max_price', type=float)
    if max_price:
        query = query.filter(Property.price <= max_price)
    
    pagination = query.order_by(db.desc(Property.created_at)).paginate(page=page, per_page=per_page, error_out=False)
    properties = pagination.items
    
    # Get unique locations for filter dropdown
    locations = db.session.query(Property.location).distinct().all()
    locations = [loc[0] for loc in locations]
    
    return render_template('properties.html', 
                           properties=properties,
                           pagination=pagination,
                           locations=locations,
                           search=search,
                           property_type=property_type,
                           location=location,
                           min_price=min_price,
                           max_price=max_price)

@public_bp.route('/property/<slug>')
def property_detail(slug):
    prop = Property.query.filter_by(slug=slug, status='available').first_or_404()
    related = Property.query.filter(
        Property.id != prop.id,
        Property.status == 'available',
        or_(Property.location == prop.location, Property.property_type == prop.property_type)
    ).limit(3).all()
    return render_template(
        'property_detail.html',
        property=prop,
        related_properties=related,
        meta_description=f"{prop.title} in {prop.location}. View price, details, photos, and map location from Baye Homes."
    )

@public_bp.route('/blog')
def blog():
    page = request.args.get('page', 1, type=int)
    per_page = 6
    posts = BlogPost.query.filter_by(is_published=True).order_by(db.desc(BlogPost.created_at)).paginate(page=page, per_page=per_page)
    return render_template('blog.html', posts=posts)

@public_bp.route('/blog/<slug>')
def blog_detail(slug):
    post = BlogPost.query.filter_by(slug=slug, is_published=True).first_or_404()
    post.views += 1
    db.session.commit()
    return render_template('blog_detail.html', post=post)

@public_bp.route('/search-suggestions')
def search_suggestions():
    q = request.args.get('q', '')
    if len(q) < 2:
        return jsonify([])
    props = Property.query.filter(Property.title.contains(q)).limit(5).all()
    suggestions = [{'title': p.title, 'url': f'/property/{p.slug}'} for p in props]
    return jsonify(suggestions)
