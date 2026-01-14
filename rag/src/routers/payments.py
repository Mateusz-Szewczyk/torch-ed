"""
Stripe Payments Router for TorchED Subscriptions
Handles checkout session creation and webhook processing
"""

import logging
import os
from typing import Optional
from datetime import datetime

import stripe
from fastapi import APIRouter, Depends, HTTPException, Request, Header
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..dependencies import get_db
from ..auth import get_current_user
from ..models import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Initialize Stripe with secret key
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

# Price IDs for plans (should be in .env)
# NOTE: These must be Price IDs from Stripe (e.g., price_1234...), NOT amounts.
STRIPE_PRICES = {
    "pro": os.getenv("STRIPE_PRICE_PRO"),
    "expert": os.getenv("STRIPE_PRICE_EXPERT"),
}

# Role mapping
ROLE_MAP = {
    "pro": "pro",
    "expert": "expert",
}

# Frontend URLs
FRONTEND_URL = os.getenv("FRONTEND_URL", "https://www.torched.pl")


class CreateCheckoutRequest(BaseModel):
    plan_id: str  # 'pro' or 'expert'


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


@router.post("/create-checkout-session", response_model=CheckoutResponse)
async def create_checkout_session(
    request: CreateCheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a Stripe Checkout session for subscription purchase.

    - Validates plan_id
    - Creates Stripe session with user metadata
    - Returns checkout URL for redirect
    """
    try:
        plan_id = request.plan_id.lower()

        if plan_id not in STRIPE_PRICES:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan_id}")

        price_id = STRIPE_PRICES[plan_id]

        if not price_id or price_id.isdigit():
            logger.error(f"Invalid Stripe Price ID for plan {plan_id}: {price_id}")
            raise HTTPException(
                status_code=500,
                detail="Server configuration error: Invalid Stripe Price ID. Please check .env configuration."
            )

        target_role = ROLE_MAP[plan_id]

        # Check if user already has this or higher role
        if current_user.role == target_role:
            raise HTTPException(
                status_code=400,
                detail=f"You already have the {target_role} plan"
            )

        if current_user.role == "expert" and target_role == "pro":
            raise HTTPException(
                status_code=400,
                detail="You cannot downgrade from Expert to Pro"
            )

        logger.info(f"Creating checkout session for user {current_user.id_}, plan: {plan_id}")

        # Create Stripe Checkout session
        checkout_session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[
                {
                    "price": price_id,
                    "quantity": 1,
                }
            ],
            # IMPORTANT: Pass user metadata for webhook processing
            metadata={
                "user_id": str(current_user.id_),
                "target_role": target_role,
                "user_email": current_user.email,
            },
            customer_email=current_user.email,
            success_url=f"{FRONTEND_URL}?payment=success&session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{FRONTEND_URL}?payment=cancelled",
            # Allow automatic tax calculation if needed
            automatic_tax={"enabled": False},
            # Customer can update billing during checkout
            billing_address_collection="required",
            # Subscription settings
            subscription_data={
                "metadata": {
                    "user_id": str(current_user.id_),
                    "target_role": target_role,
                }
            },
            # Locale for Polish users
            locale="auto",
        )

        logger.info(f"Checkout session created: {checkout_session.id}")

        return CheckoutResponse(
            checkout_url=checkout_session.url,
            session_id=checkout_session.id,
        )

    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
    except Exception as e:
        logger.error(f"Error creating checkout session: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create checkout session")


# =============================================================================
# PAYMENT INTENT - For Native Payment Sheet (In-App Checkout)
# =============================================================================

class CreatePaymentIntentRequest(BaseModel):
    plan_id: str  # 'pro' or 'expert'


class PaymentIntentResponse(BaseModel):
    client_secret: str
    ephemeral_key: str
    customer_id: str
    payment_intent_id: str


def _get_or_create_stripe_customer(user: User, db: Session) -> str:
    """
    Gets existing Stripe customer or creates a new one.
    Stores stripe_customer_id on user for future use.
    """
    # Check if user already has a Stripe customer ID
    if hasattr(user, 'stripe_customer_id') and user.stripe_customer_id:
        try:
            # Verify customer still exists in Stripe
            stripe.Customer.retrieve(user.stripe_customer_id)
            return user.stripe_customer_id
        except stripe.error.InvalidRequestError:
            # Customer was deleted, create new one
            pass

    # Create new Stripe customer
    customer = stripe.Customer.create(
        email=user.email,
        name=user.user_name,
        metadata={
            "torched_user_id": str(user.id_),
        }
    )

    # Store customer ID on user (if field exists)
    if hasattr(user, 'stripe_customer_id'):
        user.stripe_customer_id = customer.id
        db.commit()

    return customer.id


# Price amounts in cents (for PaymentIntent - one-time representation of subscription)
# These are backup values - prefer using Stripe Prices
PLAN_AMOUNTS = {
    "pro": 1900,   # 19 PLN in grosze
    "expert": 2900,  # 29 PLN in grosze
}


@router.post("/create-payment-intent", response_model=PaymentIntentResponse)
async def create_payment_intent(
    request: CreatePaymentIntentRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Creates a PaymentIntent and EphemeralKey for native Payment Sheet.

    This endpoint is used by the Flutter app to display the native Stripe
    Payment Sheet instead of redirecting to external browser.

    Returns:
        - client_secret: For Payment Sheet initialization
        - ephemeral_key: For customer session
        - customer_id: Stripe customer ID
        - payment_intent_id: For tracking
    """
    try:
        # Validate Stripe configuration
        if not stripe.api_key:
            logger.error("STRIPE_SECRET_KEY not configured")
            raise HTTPException(
                status_code=500,
                detail="Payment system not configured. Please contact support."
            )

        plan_id = request.plan_id.lower()

        if plan_id not in STRIPE_PRICES:
            raise HTTPException(status_code=400, detail=f"Invalid plan: {plan_id}")

        target_role = ROLE_MAP[plan_id]

        # Check if user already has this or higher role
        if current_user.role == target_role:
            raise HTTPException(
                status_code=400,
                detail=f"You already have the {target_role} plan"
            )

        if current_user.role == "expert" and target_role == "pro":
            raise HTTPException(
                status_code=400,
                detail="You cannot downgrade from Expert to Pro"
            )

        logger.info(f"Creating payment intent for user {current_user.id_}, plan: {plan_id}")

        # Get or create Stripe customer
        customer_id = _get_or_create_stripe_customer(current_user, db)
        logger.info(f"Using Stripe customer: {customer_id}")

        # Create ephemeral key for customer
        ephemeral_key = stripe.EphemeralKey.create(
            customer=customer_id,
            stripe_version="2023-10-16",
        )
        logger.info(f"Ephemeral key created")

        # Get amount for the plan
        amount = PLAN_AMOUNTS.get(plan_id, 1900)

        # Create PaymentIntent
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency="pln",
            customer=customer_id,
            # Enable automatic payment methods (BLIK, P24, cards, etc.)
            automatic_payment_methods={
                "enabled": True,
            },
            metadata={
                "user_id": str(current_user.id_),
                "target_role": target_role,
                "user_email": current_user.email,
                "plan_id": plan_id,
            },
            # Description shown on bank statement
            statement_descriptor_suffix="TORCHED",
            description=f"TorchED {plan_id.capitalize()} Subscription",
        )

        logger.info(f"Payment intent created: {payment_intent.id}")

        # Validate that we got a valid client_secret
        if not payment_intent.client_secret:
            logger.error(f"PaymentIntent {payment_intent.id} has no client_secret")
            raise HTTPException(
                status_code=500,
                detail="Payment intent created but missing client_secret"
            )

        if not ephemeral_key.secret:
            logger.error("EphemeralKey has no secret")
            raise HTTPException(
                status_code=500,
                detail="Ephemeral key created but missing secret"
            )

        return PaymentIntentResponse(
            client_secret=payment_intent.client_secret,
            ephemeral_key=ephemeral_key.secret,
            customer_id=customer_id,
            payment_intent_id=payment_intent.id,
        )

    except stripe.error.AuthenticationError as e:
        logger.error(f"Stripe authentication error: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Payment system authentication failed. Please contact support."
        )
    except stripe.error.StripeError as e:
        logger.error(f"Stripe error: {str(e)}")
        raise HTTPException(status_code=400, detail=f"Payment error: {str(e)}")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating payment intent: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to create payment intent")


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: Optional[str] = Header(None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """
    Handles Stripe webhooks for payment events.

    SECURITY: Verifies webhook signature before processing.

    Handles:
    - checkout.session.completed: Updates user role after successful payment
    """
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not webhook_secret:
        logger.error("STRIPE_WEBHOOK_SECRET not configured")
        raise HTTPException(status_code=500, detail="Webhook not configured")

    if not stripe_signature:
        logger.warning("Missing Stripe-Signature header")
        raise HTTPException(status_code=400, detail="Missing signature")

    try:
        # Get raw body
        payload = await request.body()

        # Verify webhook signature
        event = stripe.Webhook.construct_event(
            payload,
            stripe_signature,
            webhook_secret
        )

        logger.info(f"Webhook received: {event['type']}")

        # Handle the event
        if event["type"] == "checkout.session.completed":
            session = event["data"]["object"]
            await _handle_checkout_completed(session, db)

        elif event["type"] == "payment_intent.succeeded":
            # Handle Payment Sheet successful payment
            payment_intent = event["data"]["object"]
            await _handle_payment_intent_succeeded(payment_intent, db)

        elif event["type"] == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            logger.warning(f"Payment intent failed: {payment_intent['id']}")
            # Could notify user here

        elif event["type"] == "customer.subscription.updated":
            subscription = event["data"]["object"]
            logger.info(f"Subscription updated: {subscription['id']}")
            # Could handle plan changes here

        elif event["type"] == "customer.subscription.deleted":
            subscription = event["data"]["object"]
            await _handle_subscription_cancelled(subscription, db)

        elif event["type"] == "invoice.payment_failed":
            invoice = event["data"]["object"]
            logger.warning(f"Payment failed for invoice: {invoice['id']}")
            # Could notify user or handle grace period

        return JSONResponse(content={"status": "success"})

    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Invalid signature: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid signature")
    except Exception as e:
        logger.error(f"Webhook error: {str(e)}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")


async def _handle_checkout_completed(session: dict, db: Session):
    """
    Handles successful checkout - updates user role.

    IDEMPOTENT: Checks if user already has the target role.
    """
    try:
        metadata = session.get("metadata", {})
        user_id = metadata.get("user_id")
        target_role = metadata.get("target_role")

        if not user_id or not target_role:
            logger.error(f"Missing metadata in session: {session.get('id')}")
            return

        logger.info(f"Processing checkout for user {user_id}, target role: {target_role}")

        # Find user
        user = db.query(User).filter(User.id_ == int(user_id)).first()

        if not user:
            logger.error(f"User not found: {user_id}")
            return

        # Idempotency check
        if user.role == target_role:
            logger.info(f"User {user_id} already has role {target_role}, skipping")
            return

        # Update role
        old_role = user.role
        user.role = target_role
        db.commit()

        logger.info(f"User {user_id} role updated: {old_role} -> {target_role}")

    except Exception as e:
        logger.error(f"Error handling checkout: {str(e)}")
        db.rollback()
        raise


async def _handle_payment_intent_succeeded(payment_intent: dict, db: Session):
    """
    Handles successful PaymentIntent from Payment Sheet.
    Updates user role based on metadata.

    IDEMPOTENT: Checks if user already has the target role.
    """
    try:
        metadata = payment_intent.get("metadata", {})
        user_id = metadata.get("user_id")
        target_role = metadata.get("target_role")

        if not user_id or not target_role:
            logger.error(f"Missing metadata in payment_intent: {payment_intent.get('id')}")
            return

        logger.info(f"Processing payment intent for user {user_id}, target role: {target_role}")

        # Find user
        user = db.query(User).filter(User.id_ == int(user_id)).first()

        if not user:
            logger.error(f"User not found: {user_id}")
            return

        # Idempotency check
        if user.role == target_role:
            logger.info(f"User {user_id} already has role {target_role}, skipping")
            return

        # Update role
        old_role = user.role
        user.role = target_role
        db.commit()

        logger.info(f"User {user_id} role updated via Payment Sheet: {old_role} -> {target_role}")

    except Exception as e:
        logger.error(f"Error handling payment intent: {str(e)}")
        db.rollback()
        raise


async def _handle_subscription_cancelled(subscription: dict, db: Session):
    """
    Handles subscription cancellation - downgrades user to free.
    """
    try:
        metadata = subscription.get("metadata", {})
        user_id = metadata.get("user_id")

        if not user_id:
            logger.warning("No user_id in subscription metadata")
            return

        user = db.query(User).filter(User.id_ == int(user_id)).first()

        if not user:
            logger.error(f"User not found: {user_id}")
            return

        # Downgrade to free
        old_role = user.role
        user.role = "user"
        db.commit()

        logger.info(f"User {user_id} downgraded from {old_role} to free (subscription cancelled)")

    except Exception as e:
        logger.error(f"Error handling cancellation: {str(e)}")
        db.rollback()
        raise


@router.get("/plans")
async def get_subscription_plans():
    """
    Returns available subscription plans with pricing.
    """
    return {
        "plans": [
            {
                "id": "free",
                "name": "Free",
                "price": 0,
                "currency": "PLN",
                "period": "forever",
                "features": [
                    "3 uploaded files",
                    "5 flashcard decks",
                    "50 AI questions per week",
                    "Basic chat support",
                ],
                "limits": {
                    "files": 3,
                    "decks": 5,
                    "questions_per_period": 50,
                },
            },
            {
                "id": "pro",
                "name": "Pro",
                "price": 19,
                "currency": "PLN",
                "period": "month",
                "features": [
                    "10 uploaded files",
                    "20 flashcard decks",
                    "500 AI questions per month",
                    "Priority chat support",
                    "Advanced analytics",
                ],
                "limits": {
                    "files": 10,
                    "decks": 20,
                    "questions_per_period": 500,
                },
                "popular": True,
            },
            {
                "id": "expert",
                "name": "Expert",
                "price": 29,
                "currency": "PLN",
                "period": "month",
                "features": [
                    "Unlimited files",
                    "Unlimited flashcard decks",
                    "Unlimited AI questions",
                ],
                "limits": {
                    "files": -1,
                    "decks": -1,
                    "questions_per_period": -1,
                },
            },
        ]
    }


@router.get("/verify-session/{session_id}")
async def verify_checkout_session(
    session_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Verifies a checkout session status.
    Used by frontend to confirm payment.
    """
    try:
        session = stripe.checkout.Session.retrieve(session_id)

        # Verify session belongs to current user
        if session.metadata.get("user_id") != str(current_user.id_):
            raise HTTPException(status_code=403, detail="Session does not belong to user")

        return {
            "status": session.status,
            "payment_status": session.payment_status,
            "customer_email": session.customer_email,
        }

    except stripe.error.StripeError as e:
        logger.error(f"Error verifying session: {str(e)}")
        raise HTTPException(status_code=400, detail="Invalid session")

