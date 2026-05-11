# -*- encoding: utf-8 -*-
"""
Payment Model
"""

from datetime import datetime
from apps import db


class Payment(db.Model):

    __tablename__ = 'payments'

    id                   = db.Column(db.Integer, primary_key=True)
    stripe_session_id    = db.Column(db.String(256), unique=True, nullable=False)
    stripe_payment_intent = db.Column(db.String(256), nullable=True)
    amount               = db.Column(db.Integer, nullable=False)  # in cents
    currency             = db.Column(db.String(10), default='eur')
    status               = db.Column(db.String(50), default='pending')
    user_id              = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    customer_email       = db.Column(db.String(256), nullable=True)
    created_at           = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('Users', backref=db.backref('payments', lazy=True))

    def __repr__(self):
        return f"Payment #{self.id} - {self.amount/100} {self.currency} ({self.status})"
