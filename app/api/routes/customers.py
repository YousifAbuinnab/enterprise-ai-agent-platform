import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.crud import customer as customer_crud
from app.db.session import get_db
from app.schemas.customer import CustomerCreate, CustomerRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/customers", tags=["customers"])


@router.post("", response_model=CustomerRead, status_code=201)
def create_customer(customer_in: CustomerCreate, db: Session = Depends(get_db)) -> CustomerRead:
    """Create a new customer. Returns 409 if the email is already registered."""
    try:
        customer = customer_crud.create_customer(db, customer_in)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="A customer with this email already exists")
    return CustomerRead.model_validate(customer)


@router.get("", response_model=list[CustomerRead])
def list_customers(db: Session = Depends(get_db)) -> list[CustomerRead]:
    """List all customers."""
    customers = customer_crud.list_customers(db)
    return [CustomerRead.model_validate(c) for c in customers]


@router.get("/{customer_id}", response_model=CustomerRead)
def get_customer(customer_id: int, db: Session = Depends(get_db)) -> CustomerRead:
    """Retrieve a single customer by id. Returns 404 if not found."""
    customer = customer_crud.get_customer(db, customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail="Customer not found")
    return CustomerRead.model_validate(customer)
