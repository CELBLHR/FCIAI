from app import db
from datetime import datetime

class Translation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    english = db.Column(db.String(500), nullable=False)
    chinese = db.Column(db.String(500), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = db.relationship('User', backref=db.backref('translations', lazy=True))
    
    def __repr__(self):
        return f'<Translation {self.english} -> {self.chinese}>' 