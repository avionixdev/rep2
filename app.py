import os
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, abort
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import uuid

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py', silent=True)
app.config.setdefault('SECRET_KEY', 'dev-secret-change-me')
app.config.setdefault('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db')
app.config.setdefault('SQLALCHEMY_TRACK_MODIFICATIONS', False)

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# Models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    def to_dict(self):
        return {'id': self.id, 'username': self.username}

class Note(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    uuid = db.Column(db.String(36), unique=True, nullable=False, default=lambda: str(uuid.uuid4()))
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    owner = db.relationship('User', backref='notes')

class ACL(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    note_id = db.Column(db.Integer, db.ForeignKey('note.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    acl_type = db.Column(db.String(10), nullable=False)  # 'allow' or 'block'
    user = db.relationship('User')

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@app.before_first_request
def create_tables():
    db.create_all()

# Auth routes
@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        if not username or not password:
            flash('모든 항목을 입력하세요.')
            return redirect(url_for('register'))
        if User.query.filter_by(username=username).first():
            flash('이미 존재하는 사용자입니다.')
            return redirect(url_for('register'))
        u = User(username=username, password=generate_password_hash(password))
        db.session.add(u); db.session.commit()
        flash('회원가입 완료. 로그인 해주세요.')
        return redirect(url_for('login'))
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username','').strip()
        password = request.form.get('password','')
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            flash('로그인 성공.')
            return redirect(url_for('index'))
        flash('로그인 실패.')
        return redirect(url_for('login'))
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('로그아웃되었습니다.')
    return redirect(url_for('login'))

# Notes
@app.route('/')
@login_required
def index():
    notes = Note.query.filter_by(owner_id=current_user.id).order_by(Note.id.desc()).all()
    return render_template('index.html', notes=notes)

@app.route('/new', methods=['GET','POST'])
@login_required
def new_note():
    if request.method == 'POST':
        title = request.form.get('title','').strip()
        content = request.form.get('content','').strip()
        allowed = request.form.get('allowed_users','').strip()
        blocked = request.form.get('blocked_users','').strip()
        if not title:
            flash('제목 입력하세요.')
            return redirect(url_for('new_note'))
        note = Note(title=title, content=content, owner_id=current_user.id)
        db.session.add(note); db.session.flush()
        # add ACL entries
        for uname in [u.strip() for u in (allowed or '').split(',') if u.strip()]:
            user = User.query.filter_by(username=uname).first()
            if user:
                a = ACL(note_id=note.id, user_id=user.id, acl_type='allow')
                db.session.add(a)
        for uname in [u.strip() for u in (blocked or '').split(',') if u.strip()]:
            user = User.query.filter_by(username=uname).first()
            if user:
                b = ACL(note_id=note.id, user_id=user.id, acl_type='block')
                db.session.add(b)
        db.session.commit()
        flash('메모 생성됨.')
        return redirect(url_for('index'))
    return render_template('edit_note.html', note=None, allowed_list=[], blocked_list=[])

def can_view(note, viewer):
    # owner always allowed
    if viewer and note.owner_id == viewer.id:
        return True
    if not viewer:
        return False
    # block takes precedence
    blocked = ACL.query.filter_by(note_id=note.id, user_id=viewer.id, acl_type='block').first()
    if blocked:
        return False
    allowed = ACL.query.filter_by(note_id=note.id, user_id=viewer.id, acl_type='allow').first()
    return True if allowed else False

@app.route('/note/<note_uuid>')
def view_note(note_uuid):
    note = Note.query.filter_by(uuid=note_uuid).first_or_404()
    viewer = current_user if current_user.is_authenticated else None
    if not can_view(note, viewer):
        abort(403)
    # build allow/block username lists for display (owner sees them)
    allowed_usernames = [a.user.username for a in ACL.query.filter_by(note_id=note.id, acl_type='allow').all()]
    blocked_usernames = [a.user.username for a in ACL.query.filter_by(note_id=note.id, acl_type='block').all()]
    return render_template('view_note.html', note=note, allowed_list=allowed_usernames, blocked_list=blocked_usernames)

@app.route('/edit/<note_uuid>', methods=['GET','POST'])
@login_required
def edit_note(note_uuid):
    note = Note.query.filter_by(uuid=note_uuid).first_or_404()
    if note.owner_id != current_user.id:
        abort(403)
    if request.method == 'POST':
        note.title = request.form.get('title','').strip()
        note.content = request.form.get('content','').strip()
        allowed = [u.strip() for u in (request.form.get('allowed_users','') or '').split(',') if u.strip()]
        blocked = [u.strip() for u in (request.form.get('blocked_users','') or '').split(',') if u.strip()]
        # clear existing ACLs
        ACL.query.filter_by(note_id=note.id).delete()
        # blocked entries first (block precedence)
        for uname in blocked:
            user = User.query.filter_by(username=uname).first()
            if user:
                db.session.add(ACL(note_id=note.id, user_id=user.id, acl_type='block'))
        for uname in allowed:
            if uname in blocked:
                continue
            user = User.query.filter_by(username=uname).first()
            if user:
                db.session.add(ACL(note_id=note.id, user_id=user.id, acl_type='allow'))
        db.session.commit()
        flash('수정 완료.')
        return redirect(url_for('index'))
    # prepare lists for initial rendering
    allowed_usernames = [a.user.username for a in ACL.query.filter_by(note_id=note.id, acl_type='allow').all()]
    blocked_usernames = [a.user.username for a in ACL.query.filter_by(note_id=note.id, acl_type='block').all()]
    return render_template('edit_note.html', note=note, allowed_list=allowed_usernames, blocked_list=blocked_usernames)

@app.route('/delete/<note_uuid>', methods=['POST'])
@login_required
def delete_note(note_uuid):
    note = Note.query.filter_by(uuid=note_uuid).first_or_404()
    if note.owner_id != current_user.id:
        abort(403)
    ACL.query.filter_by(note_id=note.id).delete()
    db.session.delete(note)
    db.session.commit()
    flash('삭제됨.')
    return redirect(url_for('index'))

# API for searching users (for ACL UI)
@app.route('/api/users')
@login_required
def api_users():
    q = request.args.get('q','').strip()
    if not q:
        return jsonify([])
    users = User.query.filter(User.username.contains(q)).limit(15).all()
    data = [{'id': u.id, 'username': u.username} for u in users if u.id != current_user.id]
    return jsonify(data)

@app.errorhandler(403)
def forbidden(e):
    return "권한 없음 (403)", 403

if __name__ == '__main__':
    app.run(debug=True)
