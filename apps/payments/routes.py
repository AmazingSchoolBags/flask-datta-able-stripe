# -*- encoding: utf-8 -*-
"""
Payments Routes - Stripe Checkout
"""

import os
import stripe
from flask import render_template, request, redirect, url_for, jsonify, flash, current_app
from flask_login import login_required, current_user
from apps.payments import blueprint
from apps import db
from apps.payments.models import Payment

stripe.api_key = os.getenv('STRIPE_SECRET_KEY')

DONATION_AMOUNTS = [
    {'value': 500,  'label': '5 €',  'description': 'Un café ☕'},
    {'value': 1000, 'label': '10 €', 'description': 'Un repas 🍕'},
    {'value': 2500, 'label': '25 €', 'description': 'Un boost 🚀'},
    {'value': 5000, 'label': '50 €', 'description': 'Un super soutien 💪'},
]


@blueprint.route('/support')
def support():
    """Page de soutien / donation"""
    return render_template(
        'pages/support.html',
        segment='support',
        donation_amounts=DONATION_AMOUNTS,
        stripe_public_key=os.getenv('STRIPE_PUBLIC_KEY')
    )


@blueprint.route('/create-checkout-session', methods=['POST'])
def create_checkout_session():
    """Create a Stripe Checkout Session for a donation"""
    try:
        amount = int(request.form.get('amount', 1000))

        # Validate amount
        if amount < 100:
            flash('Le montant minimum est de 1 €', 'danger')
            return redirect(url_for('payments_blueprint.support'))

        # Build success/cancel URLs
        base_url = request.host_url.rstrip('/')
        success_url = base_url + url_for('payments_blueprint.success') + '?session_id={CHECKOUT_SESSION_ID}'
        cancel_url = base_url + url_for('payments_blueprint.cancel')

        # Create Stripe Checkout Session
        checkout_session = stripe.checkout.Session.create(
            payment_method_types=['card'],
            line_items=[{
                'price_data': {
                    'currency': 'eur',
                    'product_data': {
                        'name': 'Soutenir Datta Able',
                        'description': 'Merci pour votre soutien ! 🎉',
                    },
                    'unit_amount': amount,
                },
                'quantity': 1,
            }],
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            metadata={
                'user_id': current_user.id if current_user.is_authenticated else 'anonymous',
                'username': current_user.username if current_user.is_authenticated else 'anonymous',
            }
        )

        return redirect(checkout_session.url, code=303)

    except stripe.error.StripeError as e:
        flash(f'Erreur Stripe : {str(e)}', 'danger')
        return redirect(url_for('payments_blueprint.support'))
    except Exception as e:
        flash(f'Erreur : {str(e)}', 'danger')
        return redirect(url_for('payments_blueprint.support'))


@blueprint.route('/success')
def success():
    """Payment success page"""
    session_id = request.args.get('session_id')
    session_data = None

    if session_id:
        try:
            session_data = stripe.checkout.Session.retrieve(session_id)

            # Save payment to database
            payment = Payment(
                stripe_session_id=session_id,
                stripe_payment_intent=session_data.payment_intent,
                amount=session_data.amount_total,
                currency=session_data.currency,
                status='completed',
                user_id=current_user.id if current_user.is_authenticated else None,
                customer_email=session_data.customer_details.email if session_data.customer_details else None,
            )
            # Avoid duplicates
            existing = Payment.query.filter_by(stripe_session_id=session_id).first()
            if not existing:
                db.session.add(payment)
                db.session.commit()

        except Exception as e:
            current_app.logger.error(f'Error retrieving session: {e}')

    return render_template(
        'pages/payment-success.html',
        segment='support',
        session_data=session_data
    )


@blueprint.route('/cancel')
def cancel():
    """Payment cancelled page"""
    return render_template('pages/payment-cancel.html', segment='support')


@blueprint.route('/webhook', methods=['POST'])
def webhook():
    """Stripe Webhook endpoint"""
    payload = request.get_data(as_text=True)
    sig_header = request.headers.get('Stripe-Signature')
    endpoint_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        if endpoint_secret:
            event = stripe.Webhook.construct_event(payload, sig_header, endpoint_secret)
        else:
            event = stripe.Event.construct_from(
                stripe.util.json.loads(payload), stripe.api_key
            )
    except ValueError:
        return jsonify({'error': 'Invalid payload'}), 400
    except stripe.error.SignatureVerificationError:
        return jsonify({'error': 'Invalid signature'}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        current_app.logger.info(f"Payment completed: {session['id']}")

    return jsonify({'status': 'success'}), 200
