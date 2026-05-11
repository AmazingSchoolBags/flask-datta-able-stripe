# -*- encoding: utf-8 -*-
"""
Payments Blueprint - Stripe Integration
"""

from flask import Blueprint

blueprint = Blueprint(
    'payments_blueprint',
    __name__,
    url_prefix='/payments'
)
