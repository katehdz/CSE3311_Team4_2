from __future__ import annotations
import os
import sys
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Optional, List
import json

from dotenv import load_dotenv
import firebase_admin
from firebase_admin import credentials, firestore
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash

# ── bootstrap
load_dotenv()
sa_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
project_id = os.getenv("FIREBASE_PROJECT_ID")

if not sa_path or not os.path.exists(sa_path):
    print("ERROR: Set GOOGLE_APPLICATION_CREDENTIALS in .env to your service account JSON path.")
    sys.exit(1)

if not project_id:
    print("ERROR: Set FIREBASE_PROJECT_ID in .env to your Firebase project id.")
    sys.exit(1)

cred = credentials.Certificate(sa_path)
firebase_admin.initialize_app(cred, {"projectId": project_id})
db = firestore.client()

# ── data classes (with fixed deprecation warnings)
@dataclass
class University:
    name: str
    domain: Optional[str] = None
    createdAt: datetime = None

    def __post_init__(self):
        if self.createdAt is None:
            self.createdAt = datetime.now(timezone.utc)

@dataclass
class Club:
    name: str
    universityId: str
    description: Optional[str] = None
    createdAt: datetime = None

    def __post_init__(self):
        if self.createdAt is None:
            self.createdAt = datetime.now(timezone.utc)

@dataclass
class Person:
    name: str
    email: Optional[str] = None
    studentId: Optional[str] = None
    createdAt: datetime = None

    def __post_init__(self):
        if self.createdAt is None:
            self.createdAt = datetime.now(timezone.utc)

@dataclass
class Membership:
    personId: str
    role: str = "member"         # "owner"|"officer"|"member"
    status: str = "active"       # "active"|"inactive"
    title: Optional[str] = None
    createdAt: datetime = None

    def __post_init__(self):
        if self.createdAt is None:
            self.createdAt = datetime.now(timezone.utc)

# ── Flask app
app = Flask(__name__)
app.secret_key = 'your-secret-key-change-in-production'

# ── Helper functions
def doc_to_dict_with_id(doc):
    """Convert Firestore document to dict with id included"""
    data = doc.to_dict()
    data['id'] = doc.id
    return data

def format_datetime(dt):
    """Format datetime for display"""
    if isinstance(dt, datetime):
        return dt.strftime('%Y-%m-%d %H:%M')
    return str(dt)

app.jinja_env.filters['datetime'] = format_datetime

# ── Routes

@app.route('/')
def index():
    return render_template('index.html')

# ── University routes
@app.route('/universities')
def universities():
    docs = list(db.collection("universities").order_by("name").stream())
    universities_data = [doc_to_dict_with_id(doc) for doc in docs]
    return render_template('universities.html', universities=universities_data)

@app.route('/universities/create', methods=['GET', 'POST'])
def create_university():
    if request.method == 'POST':
        name = request.form['name'].strip()
        domain = request.form['domain'].strip() or None
        
        if not name:
            flash('University name is required', 'error')
            return render_template('create_university.html')
        
        ref = db.collection("universities").document()
        ref.set(asdict(University(name=name, domain=domain)))
        flash(f'University "{name}" created successfully!', 'success')
        return redirect(url_for('universities'))
    
    return render_template('create_university.html')

@app.route('/universities/<university_id>/edit', methods=['GET', 'POST'])
def edit_university(university_id):
    doc = db.collection("universities").document(university_id).get()
    if not doc.exists:
        flash('University not found', 'error')
        return redirect(url_for('universities'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        domain = request.form['domain'].strip() or None
        
        if not name:
            flash('University name is required', 'error')
            return render_template('edit_university.html', university=doc_to_dict_with_id(doc))
        
        doc.reference.update({"name": name, "domain": domain})
        flash(f'University "{name}" updated successfully!', 'success')
        return redirect(url_for('universities'))
    
    return render_template('edit_university.html', university=doc_to_dict_with_id(doc))

@app.route('/universities/<university_id>/delete', methods=['POST'])
def delete_university(university_id):
    doc = db.collection("universities").document(university_id).get()
    if doc.exists:
        doc.reference.delete()
        flash('University deleted successfully!', 'success')
    else:
        flash('University not found', 'error')
    return redirect(url_for('universities'))

# ── Club routes
@app.route('/clubs')
def clubs():
    docs = list(db.collection("clubs").order_by("name").stream())
    clubs_data = []
    
    for doc in docs:
        club_data = doc_to_dict_with_id(doc)
        # Get university name
        uni_doc = db.collection("universities").document(club_data['universityId']).get()
        club_data['universityName'] = uni_doc.to_dict().get('name', 'Unknown') if uni_doc.exists else 'Unknown'
        clubs_data.append(club_data)
    
    return render_template('clubs.html', clubs=clubs_data)

@app.route('/clubs/create', methods=['GET', 'POST'])
def create_club():
    if request.method == 'POST':
        name = request.form['name'].strip()
        university_id = request.form['universityId']
        description = request.form['description'].strip() or None
        
        if not name or not university_id:
            flash('Club name and university are required', 'error')
            universities_data = [doc_to_dict_with_id(doc) for doc in db.collection("universities").order_by("name").stream()]
            return render_template('create_club.html', universities=universities_data)
        
        ref = db.collection("clubs").document()
        ref.set(asdict(Club(name=name, universityId=university_id, description=description)))
        flash(f'Club "{name}" created successfully!', 'success')
        return redirect(url_for('clubs'))
    
    universities_data = [doc_to_dict_with_id(doc) for doc in db.collection("universities").order_by("name").stream()]
    return render_template('create_club.html', universities=universities_data)

@app.route('/clubs/<club_id>/edit', methods=['GET', 'POST'])
def edit_club(club_id):
    doc = db.collection("clubs").document(club_id).get()
    if not doc.exists:
        flash('Club not found', 'error')
        return redirect(url_for('clubs'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        description = request.form['description'].strip() or None
        
        if not name:
            flash('Club name is required', 'error')
            return render_template('edit_club.html', club=doc_to_dict_with_id(doc))
        
        doc.reference.update({"name": name, "description": description})
        flash(f'Club "{name}" updated successfully!', 'success')
        return redirect(url_for('clubs'))
    
    return render_template('edit_club.html', club=doc_to_dict_with_id(doc))

@app.route('/clubs/<club_id>/delete', methods=['POST'])
def delete_club(club_id):
    doc = db.collection("clubs").document(club_id).get()
    if doc.exists:
        # Delete memberships first
        mem_docs = list(doc.reference.collection("memberships").stream())
        batch = db.batch()
        for mem_doc in mem_docs:
            batch.delete(mem_doc.reference)
        batch.delete(doc.reference)
        batch.commit()
        flash('Club and its memberships deleted successfully!', 'success')
    else:
        flash('Club not found', 'error')
    return redirect(url_for('clubs'))

# ── People routes
@app.route('/people')
def people():
    docs = list(db.collection("people").order_by("name").stream())
    people_data = [doc_to_dict_with_id(doc) for doc in docs]
    return render_template('people.html', people=people_data)

@app.route('/people/create', methods=['GET', 'POST'])
def create_person():
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip() or None
        student_id = request.form['studentId'].strip() or None
        
        if not name:
            flash('Person name is required', 'error')
            return render_template('create_person.html')
        
        ref = db.collection("people").document()
        ref.set(asdict(Person(name=name, email=email, studentId=student_id)))
        flash(f'Person "{name}" created successfully!', 'success')
        return redirect(url_for('people'))
    
    return render_template('create_person.html')

@app.route('/people/<person_id>/edit', methods=['GET', 'POST'])
def edit_person(person_id):
    doc = db.collection("people").document(person_id).get()
    if not doc.exists:
        flash('Person not found', 'error')
        return redirect(url_for('people'))
    
    if request.method == 'POST':
        name = request.form['name'].strip()
        email = request.form['email'].strip() or None
        student_id = request.form['studentId'].strip() or None
        
        if not name:
            flash('Person name is required', 'error')
            return render_template('edit_person.html', person=doc_to_dict_with_id(doc))
        
        doc.reference.update({"name": name, "email": email, "studentId": student_id})
        flash(f'Person "{name}" updated successfully!', 'success')
        return redirect(url_for('people'))
    
    return render_template('edit_person.html', person=doc_to_dict_with_id(doc))

@app.route('/people/<person_id>/delete', methods=['POST'])
def delete_person(person_id):
    doc = db.collection("people").document(person_id).get()
    if doc.exists:
        doc.reference.delete()
        flash('Person deleted successfully!', 'success')
    else:
        flash('Person not found', 'error')
    return redirect(url_for('people'))

# ── Membership routes
@app.route('/clubs/<club_id>/members')
def club_members(club_id):
    club_doc = db.collection("clubs").document(club_id).get()
    if not club_doc.exists:
        flash('Club not found', 'error')
        return redirect(url_for('clubs'))
    
    club_data = doc_to_dict_with_id(club_doc)
    mem_docs = list(club_doc.reference.collection("memberships").stream())
    
    members_data = []
    for mem_doc in mem_docs:
        mem_data = doc_to_dict_with_id(mem_doc)
        person_doc = db.collection("people").document(mem_data['personId']).get()
        mem_data['personName'] = person_doc.to_dict().get('name', 'Unknown') if person_doc.exists else 'Unknown'
        mem_data['personEmail'] = person_doc.to_dict().get('email', '') if person_doc.exists else ''
        members_data.append(mem_data)
    
    return render_template('club_members.html', club=club_data, members=members_data)

@app.route('/clubs/<club_id>/members/add', methods=['GET', 'POST'])
def add_member(club_id):
    club_doc = db.collection("clubs").document(club_id).get()
    if not club_doc.exists:
        flash('Club not found', 'error')
        return redirect(url_for('clubs'))
    
    if request.method == 'POST':
        person_id = request.form['personId']
        role = request.form['role'] or 'member'
        status = request.form['status'] or 'active'
        title = request.form['title'].strip() or None
        
        if not person_id:
            flash('Person is required', 'error')
            people_data = [doc_to_dict_with_id(doc) for doc in db.collection("people").order_by("name").stream()]
            return render_template('add_member.html', club=doc_to_dict_with_id(club_doc), people=people_data)
        
        ref = club_doc.reference.collection("memberships").document()
        ref.set(asdict(Membership(personId=person_id, role=role, status=status, title=title)))
        flash('Member added successfully!', 'success')
        return redirect(url_for('club_members', club_id=club_id))
    
    people_data = [doc_to_dict_with_id(doc) for doc in db.collection("people").order_by("name").stream()]
    return render_template('add_member.html', club=doc_to_dict_with_id(club_doc), people=people_data)

@app.route('/clubs/<club_id>/members/<member_id>/edit', methods=['GET', 'POST'])
def edit_member(club_id, member_id):
    club_doc = db.collection("clubs").document(club_id).get()
    if not club_doc.exists:
        flash('Club not found', 'error')
        return redirect(url_for('clubs'))
    
    mem_doc = club_doc.reference.collection("memberships").document(member_id).get()
    if not mem_doc.exists:
        flash('Member not found', 'error')
        return redirect(url_for('club_members', club_id=club_id))
    
    if request.method == 'POST':
        role = request.form['role'] or 'member'
        status = request.form['status'] or 'active'
        title = request.form['title'].strip() or None
        
        mem_doc.reference.update({"role": role, "status": status, "title": title})
        flash('Member updated successfully!', 'success')
        return redirect(url_for('club_members', club_id=club_id))
    
    member_data = doc_to_dict_with_id(mem_doc)
    person_doc = db.collection("people").document(member_data['personId']).get()
    member_data['personName'] = person_doc.to_dict().get('name', 'Unknown') if person_doc.exists else 'Unknown'
    
    return render_template('edit_member.html', club=doc_to_dict_with_id(club_doc), member=member_data)

@app.route('/clubs/<club_id>/members/<member_id>/delete', methods=['POST'])
def delete_member(club_id, member_id):
    club_doc = db.collection("clubs").document(club_id).get()
    if club_doc.exists:
        mem_doc = club_doc.reference.collection("memberships").document(member_id).get()
        if mem_doc.exists:
            mem_doc.reference.delete()
            flash('Member removed successfully!', 'success')
        else:
            flash('Member not found', 'error')
    else:
        flash('Club not found', 'error')
    return redirect(url_for('club_members', club_id=club_id))

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5001)
