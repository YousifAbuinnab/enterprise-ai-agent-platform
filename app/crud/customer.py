from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.customer import Customer
from app.schemas.customer import CustomerCreate


def create_customer(db: Session, customer_in: CustomerCreate) -> Customer:
    """Insert a new customer row. Raises sqlalchemy.exc.IntegrityError on duplicate email."""
    customer = Customer(name=customer_in.name, email=customer_in.email, company=customer_in.company)
    db.add(customer)
    db.commit()
    db.refresh(customer)
    return customer


def list_customers(db: Session) -> list[Customer]:
    """Return all customers ordered by id."""
    return list(db.scalars(select(Customer).order_by(Customer.id)))


def get_customer(db: Session, customer_id: int) -> Customer | None:
    """Return a single customer by id, or None if not found."""
    return db.get(Customer, customer_id)
