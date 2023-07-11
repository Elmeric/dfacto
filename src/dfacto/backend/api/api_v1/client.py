# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# pylint: disable=too-many-lines

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Optional, Type

import jinja2 as jinja
from babel.dates import format_date

from dfacto import settings as Config
from dfacto.backend import crud, naming, schemas
from dfacto.backend.api.command import CommandResponse, CommandStatus, command
from dfacto.backend.models import InvoiceStatus
from dfacto.backend.util import DatetimeRange, Period, PeriodFilter

from .base import DFactoModel


@dataclass
class Company:
    # pylint: disable=too-many-instance-attributes
    name: str
    address: str
    zip_code: str
    city: str
    phone_number: str
    email: str
    siret: str
    rcs: str


@dataclass
class ClientModel(DFactoModel[crud.CRUDClient, schemas.Client]):
    # pylint: disable=too-many-public-methods
    crud_object: crud.CRUDClient = crud.client
    schema: Type[schemas.Client] = schemas.Client

    class HtmlMode(Enum):
        CREATE = 0
        SHOW = 1
        ISSUE = 2
        REMIND = 3

    def __post_init__(self) -> None:
        naming_templates = naming.NamingTemplates()

        self.destination_naming_template = naming_templates.get_default(
            naming.TemplateType.DESTINATION
        )
        self.invoice_naming_template = naming_templates.get_default(
            naming.TemplateType.INVOICE
        )

    @command
    def get_active(self) -> CommandResponse:
        try:
            clients = self.crud_object.get_active(self.session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ACTIVE - SQL or database error: {exc}",
            )
        body = [schemas.Client.from_orm(client_) for client_ in clients]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_basket(self, obj_id: int) -> CommandResponse:
        try:
            basket = self.crud_object.get_basket(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-BASKET - SQL or database error: {exc}",
            )

        if basket is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-BASKET - Basket of client {obj_id} not found.",
            )

        body = schemas.Basket.from_orm(basket)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_quantity_in_basket(
        self, obj_id: int, *, service_id: tuple[int, int]
    ) -> CommandResponse:
        try:
            basket = self.crud_object.get_basket(self.session, obj_id)
            service = crud.service.get(self.session, service_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"QTY-IN-BASKET - SQL or database error: {exc}",
            )
        if basket is None or service is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"QTY-IN-BASKET - Client {obj_id} or "
                f"service {service_id} not found.",
            )

        quantity = 0
        for item_ in basket.items:
            if item_.service_id == service.id:
                quantity = item_.quantity
                break
        return CommandResponse(CommandStatus.COMPLETED, body=quantity)

    @command
    def get_item_from_service(self, obj_id: int, *, service_id: int) -> CommandResponse:
        try:
            item_ = self.crud_object.get_item_from_service(
                self.session, obj_id, service_id=service_id
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ITEM-FROM-SERVICE - SQL or database error: {exc}",
            )

        if item_ is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ITEM-FROM-SERVICE - Service {service_id} not found.",
            )

        body = schemas.Item.from_orm(item_)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_invoices(
        self,
        obj_id: int,  # client id
        *,
        status: Optional[InvoiceStatus] = None,
        filter_: Optional[PeriodFilter] = None,
        period: Optional[Period] = None,
    ) -> CommandResponse:
        # filter on a given status (EMITTED, PAID,...), logged during a given period.
        if filter_ is not None and period is not None:
            return CommandResponse(
                CommandStatus.REJECTED,
                "'filter' and 'period' arguments are mutually exclusive.",
            )
        if filter_ is not None:
            period = filter_.as_period()
        # Here, period may be None if both filter and period was None
        if period is None:
            period = Period()  # i.e. from now to the epoch
        if status is not None:
            return self._get_invoices_by_status(obj_id, status=status, period=period)
        return self._get_invoices(obj_id, period=period)

    def _get_invoices_by_status(
        self, obj_id: int, *, status: InvoiceStatus, period: Period
    ) -> CommandResponse:
        try:
            invoices = self.crud_object.get_invoices_by_status(
                self.session, obj_id, status=status, period=period
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICES - SQL or database error: {exc}",
            )
        body = [schemas.Invoice.from_orm(invoice) for invoice in invoices]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def _get_invoices(self, obj_id: int, *, period: Period) -> CommandResponse:
        try:
            invoices = self.crud_object.get_invoices(
                self.session, obj_id, period=period
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICES - SQL or database error: {exc}",
            )
        body = [schemas.Invoice.from_orm(invoice) for invoice in invoices]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_invoice(self, *, invoice_id: int) -> CommandResponse:
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICE - SQL or database error: {exc}",
            )
        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICE - Invoice {invoice_id} not found.",
            )

        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_all_invoices(self) -> CommandResponse:
        try:
            invoices = crud.invoice.get_all(self.session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ALL-INVOICES - SQL or database error: {exc}",
            )
        body = [schemas.Invoice.from_orm(invoice) for invoice in invoices]
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    def rename(self, obj_id: int, name: str) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(name=name))

    def change_address(self, obj_id: int, address: schemas.Address) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(address=address))

    def change_email(self, obj_id: int, email: str) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(email=email))

    def set_active(self, obj_id: int) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(is_active=True))

    def set_inactive(self, obj_id: int) -> CommandResponse:
        response = self.clear_basket(obj_id)
        if response.status is not CommandStatus.COMPLETED:
            return response
        return self.update(obj_id, obj_in=schemas.ClientUpdate(is_active=False))

    @command
    def delete(self, obj_id: int) -> CommandResponse:
        try:
            client_ = self.crud_object.get(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - SQL or database error: {exc}",
            )

        if client_ is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Object {obj_id} not found.",
            )

        if client_.has_emitted_invoices:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"DELETE - Client {client_.name} has non-DRAFT invoices"
                f" and cannot be deleted.",
            )

        try:
            self.crud_object.delete(self.session, db_obj=client_)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - Cannot delete object {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)

    @command
    def add_to_basket(
        self, obj_id: int, *, service_id: int, quantity: int = 1
    ) -> CommandResponse:
        if quantity == 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                "ADD-TO-BASKET - Quantity shall not be zero",
            )
        try:
            client_ = self.crud_object.get(self.session, obj_id)
            service = crud.service.get_current(self.session, service_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-BASKET - SQL or database error: {exc}",
            )

        if client_ is None or service is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-BASKET - Client {obj_id} or "
                f"service {service_id} not found.",
            )

        if not client_.is_active:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"ADD-TO-BASKET - Client {client_.name} is inactive",
            )

        basket = client_.basket
        try:
            it = self.crud_object.add_to_basket(
                self.session, basket=basket, service=service, quantity=quantity
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-BASKET - Cannot add to basket of client {obj_id}: {exc}",
            )
        body = schemas.Item.from_orm(it)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def remove_from_basket(
        self, obj_id: int, *, service_id: tuple[int, int]
    ) -> CommandResponse:
        try:
            client_ = self.crud_object.get(self.session, obj_id)
            service = crud.service.get(self.session, service_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE_FROM-BASKET - SQL or database error: {exc}",
            )

        if client_ is None or service is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE_FROM-BASKET - Client {obj_id} or "
                f"service {service_id} not found.",
            )

        if not client_.is_active:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"REMOVE_FROM-BASKET - Client {client_.name} is inactive",
            )

        basket = client_.basket
        try:
            id_ = self.crud_object.remove_from_basket(
                self.session, basket=basket, service=service
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE_FROM-BASKET - Cannot remove {service.name} basket "
                f"of client {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED, body=id_)

    @command
    def add_to_invoice(
        self,
        obj_id: int,
        *,
        invoice_id: int,
        service_id: tuple[int, int],
        quantity: int = 1,
    ) -> CommandResponse:
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
            service = crud.service.get(self.session, service_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None or service is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-INVOICE - Invoice {invoice_id} or "
                f"service {service_id} not found.",
            )
        if invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"ADD-TO-INVOICE - Invoice {invoice_id} is not owned "
                f"by client {obj_id}.",
            )
        if invoice.status is not InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                "ADD-TO-INVOICE - Cannot add items to a non-draft invoice.",
            )

        try:
            it = crud.invoice.add_item(
                self.session, invoice_=invoice, service=service, quantity=quantity
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-INVOICE - Cannot add to invoice {invoice_id}: {exc}",
            )
        body = schemas.Item.from_orm(it)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def update_item_quantity(
        self, obj_id: int, *, item_id: int, quantity: int
    ) -> CommandResponse:
        # pylint: disable=too-many-return-statements
        if quantity <= 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                "UPDATE-ITEM - Item quantity shall be at least one.",
            )

        try:
            item = crud.item.get(self.session, item_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE-ITEM - SQL or database error: {exc}",
            )

        if item is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE-ITEM - Item {item_id} not found.",
            )

        basket = item.basket
        if basket is not None and basket.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"UPDATE-ITEM - Item {item_id} is not part of the "
                f"basket of client {obj_id}.",
            )
        invoice = item.invoice
        if invoice is not None and invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"UPDATE-ITEM - Item {item_id} is not part of any "
                f"invoice of client {obj_id}.",
            )
        if invoice is not None and invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                "UPDATE-ITEM - Cannot change items of a non-draft invoice.",
            )

        try:
            self.crud_object.update_item_quantity(
                self.session, item=item, quantity=quantity
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE-ITEM - Cannot remove item {item_id}: {exc}",
            )
        body = schemas.Item.from_orm(item)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def remove_item(self, obj_id: int, *, item_id: int) -> CommandResponse:
        # pylint: disable=too-many-return-statements
        try:
            item = crud.item.get(self.session, item_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE-ITEM - SQL or database error: {exc}",
            )

        if item is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE-ITEM - Item {item_id} not found.",
            )

        basket = item.basket
        if basket is not None and basket.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"REMOVE-ITEM - Item {item_id} is not part of the "
                f"basket of client {obj_id}.",
            )
        invoice = item.invoice
        if invoice is not None and invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"REMOVE-ITEM - Item {item_id} is not part of any "
                f"invoice of client {obj_id}.",
            )
        if invoice is not None and invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                "REMOVE-ITEM - Cannot remove items from a non-draft invoice.",
            )
        if basket is not None and invoice is not None:
            return CommandResponse(
                CommandStatus.REJECTED,
                "REMOVE-ITEM - Cannot remove items used both by the basket "
                "and an invoice.",
            )

        try:
            self.crud_object.remove_item(self.session, item=item)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE-ITEM - Cannot remove item {item_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)

    @command
    def clear_basket(self, obj_id: int) -> CommandResponse:
        try:
            basket = self.crud_object.get_basket(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLEAR-BASKET - SQL or database error: {exc}",
            )

        if basket is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLEAR-BASKET - Basket of client {obj_id} not found.",
            )

        try:
            self.crud_object.clear_basket(self.session, basket=basket)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLEAR-BASKET - Cannot clear basket of client {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)

    # emit: send in pdf in an email (optional, check yagmail or sendgrid or sendinblue.
    # Examples on Real Python)
    # remind: send a reminder in an email (optional)
    @command
    def create_invoice(self, obj_id: int) -> CommandResponse:
        try:
            invoice = crud.invoice.create(
                self.session, obj_in=schemas.InvoiceCreate(obj_id)
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE-INVOICE - Cannot create an invoice for client {obj_id}: {exc}",
            )
        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def invoice_from_basket(
        self, obj_id: int, clear_basket: bool = True
    ) -> CommandResponse:
        try:
            basket = crud.client.get_basket(self.session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE-FROM-BASKET - SQL or database error: {exc}",
            )

        if basket is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE_FROM-BASKET - Basket of client {obj_id} not found.",
            )
        if len(basket.items) <= 0:
            # No items in basket of client: create an empty invoice
            return self.create_invoice(obj_id)

        try:
            invoice = crud.invoice.invoice_from_basket(
                self.session, basket, clear_basket=clear_basket
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE_FROM-BASKET - Cannot create invoice from basket of client "
                f"{obj_id}: {exc}",
            )
        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def clear_invoice(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._clear_or_delete_invoice(obj_id, invoice_id, clear_only=True)

    @command
    def delete_invoice(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._clear_or_delete_invoice(obj_id, invoice_id, clear_only=False)

    def _clear_or_delete_invoice(
        self, obj_id: int, invoice_id: int, clear_only: bool = False
    ) -> CommandResponse:
        action = "clear" if clear_only else "delete"
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}-INVOICE - Invoice {invoice_id} not found.",
            )
        if invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"{action.upper()}-INVOICE - Invoice {invoice_id} is not an "
                f"invoice of client {obj_id}.",
            )
        if invoice.status != InvoiceStatus.DRAFT:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"{action.upper()}-INVOICE - Cannot {action} a non-draft invoice.",
            )

        try:
            if clear_only:
                crud.invoice.clear_invoice(self.session, invoice_=invoice)
            else:
                crud.invoice.delete_invoice(self.session, invoice_=invoice)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}-INVOICE - Cannot {action} invoice {invoice_id} "
                f"of client {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)

    @command
    def cancel_invoice(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._mark_as(obj_id, invoice_id, status=InvoiceStatus.CANCELLED)

    @command
    def mark_as_emitted(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._mark_as(obj_id, invoice_id, status=InvoiceStatus.EMITTED)

    @command
    def mark_as_reminded(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._mark_as(obj_id, invoice_id, status=InvoiceStatus.REMINDED)

    @command
    def mark_as_paid(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._mark_as(obj_id, invoice_id, status=InvoiceStatus.PAID)

    @command
    def mark_as_cancelled(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._mark_as(obj_id, invoice_id, status=InvoiceStatus.CANCELLED)

    def _mark_as(
        self, obj_id: int, invoice_id: int, status: InvoiceStatus
    ) -> CommandResponse:
        """
        None	    Create_invoice	            DRAFT
        DRAFT	    (emit) mark_as_emitted	    EMITTED
        DRAFT	    delete_invoice	            None
        EMITTED	    mark_as_paid	            PAID
        EMITTED	    (remind) mark_as_reminded	REMINDED
        EMITTED	    cancel_invoice	            CANCELLED
        REMINDED	mark_as_paid	            PAID
        REMINDED	(remind) mark_as_reminded	REMINDED
        REMINDED	cancel_invoice	            CANCELLED
        """
        assert status in (
            InvoiceStatus.EMITTED,
            InvoiceStatus.REMINDED,
            InvoiceStatus.PAID,
            InvoiceStatus.CANCELLED,
        )

        try:
            invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"MARK_AS-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"MARK_AS-INVOICE - Invoice {invoice_id} not found.",
            )
        if invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"MARK_AS-INVOICE - Invoice {invoice_id} is not an invoice of "
                f"client {obj_id}.",
            )
        valid_status = {
            InvoiceStatus.EMITTED: (InvoiceStatus.DRAFT,),
            InvoiceStatus.REMINDED: (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED),
            InvoiceStatus.PAID: (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED),
            InvoiceStatus.CANCELLED: (
                InvoiceStatus.EMITTED,
                InvoiceStatus.REMINDED,
            ),
        }
        if invoice.status not in valid_status[status]:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"MARK_AS-INVOICE - Invoice status transition from "
                f"{invoice.status} to {status} is not allowed.",
            )

        try:
            crud.invoice.mark_as(self.session, invoice_=invoice, status=status)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"MARK_AS-INVOICE - Cannot mark invoice {invoice_id} of "
                f"client {obj_id} as {status}: {exc}",
            )
        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def get_invoice_pathname(self, *, invoice_id: int, home: Path) -> CommandResponse:
        try:
            orm_invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-PATHNAME - SQL or database error: {exc}",
            )

        if orm_invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"INVOICE-PATHNAME - Invoice {invoice_id} not found.",
            )
        invoice = schemas.Invoice.from_orm(orm_invoice)
        destination = self.destination_naming_template.format(
            invoice, kind=naming.TemplateType.DESTINATION
        )
        filename = self.invoice_naming_template.format(
            invoice, kind=naming.TemplateType.INVOICE
        )
        if invoice.status in (InvoiceStatus.EMITTED, InvoiceStatus.REMINDED):
            filename += "-REMIND"
        folder = home / destination
        folder.mkdir(parents=True, exist_ok=True)
        pathname = (folder / filename).with_suffix(".pdf")
        return CommandResponse(CommandStatus.COMPLETED, body=pathname)

    @command
    def preview_invoice(
        self, obj_id: int, *, invoice_id: int, mode: HtmlMode
    ) -> CommandResponse:
        # pylint: disable=too-many-return-statements
        # pylint: disable=line-too-long
        # pylint: disable=too-many-locals
        """
                    SHOW	                        ISSUE	                REMIND
        DRAFT
                stamp = DRAFT	                stamp = None
                date = created_on	            date = created_on
                due_date = None	                due_date = None
        EMITTED
                stamp = ISSUED on xxx		                            stamp = REMINDER
                date = issued_on		                                date = issued_on
                due_date = date + delta		                            due_date = date + delta
        REMINDED
                stamp = REMINDED on xxx		                            stamp = nth REMINDER
                date = issued_on		                                date = issued_on
                due_date = issued_on + delta		                    due_date = date + delta
        PAID
                stamp = PAID on xxx
                date = issued_on
                due_date = issued_on + delta
        CANCELLED
                stamp = CANCELLED on xxx
                date = issued_on
                due_date = issued_on + delta
        """
        try:
            orm_client = self.crud_object.get(self.session, obj_id)
            orm_invoice = crud.invoice.get(self.session, invoice_id)
            orm_company = crud.company.get_current()
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - SQL or database error: {exc}",
            )

        if orm_client is None or orm_invoice is None or orm_company is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - Client {obj_id} or invoice {invoice_id} "
                f" or current company not found.",
            )
        if orm_invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"PREVIEW-INVOICE - Invoice {invoice_id} is not an invoice of "
                f"client {obj_id}.",
            )

        tpl_name = "invoice_no_vat.html" if orm_company.no_vat else "invoice.html"
        try:
            templates_dir = Config.dfacto_settings.templates
            template_dir = templates_dir / orm_company.home.name
            if not template_dir.exists():
                resources = Config.dfacto_settings.resources
                template_dir = resources / "invoice_template"
            env = jinja.Environment(
                loader=jinja.FileSystemLoader(template_dir.as_posix())
            )
        except ValueError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - HTML templates location not available: {exc}",
            )
        try:
            template = env.get_template(tpl_name)
        except jinja.TemplateNotFound as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - HTML template not found: {exc}",
            )
        except jinja.TemplateSyntaxError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - HTML template syntax error: {exc}",
            )

        context = self._build_context(
            client_=schemas.Client.from_orm(orm_client),
            invoice=schemas.Invoice.from_orm(orm_invoice),
            company=schemas.Company.from_orm(orm_company),
            mode=mode,
        )
        try:
            preview = template.render(context)
        except (jinja.TemplateSyntaxError, jinja.TemplateRuntimeError) as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"PREVIEW-INVOICE - HTML template rendering error: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED, body=preview)

    def _get_stamp(self, invoice: schemas.Invoice, mode: HtmlMode) -> tuple[str, str]:
        # pylint: disable=too-many-return-statements
        status = invoice.status

        if mode in (self.HtmlMode.CREATE, self.HtmlMode.ISSUE):
            return "", "is-empty"

        if mode is self.HtmlMode.REMIND:
            if status is InvoiceStatus.EMITTED:
                return "Rappel", "is-bad"
            if status is InvoiceStatus.REMINDED:
                return "Second Rappel", "is-bad"
            return "", "is-empty"

        if mode is self.HtmlMode.SHOW:
            locale = Config.dfacto_settings.locale
            if status is InvoiceStatus.DRAFT:
                return "DRAFT", "is-draft"
            if status is InvoiceStatus.EMITTED:
                changed_on = invoice.issued_on
                assert changed_on is not None
                date_ = format_date(changed_on.date(), format="long", locale=locale)
                return f"Emise le {date_}", "is-ok"
            if status is InvoiceStatus.REMINDED:
                changed_on = invoice.reminded_on
                assert changed_on is not None
                date_ = format_date(changed_on.date(), format="long", locale=locale)
                return f"Rappel le {date_}", "is-bad"
            if status is InvoiceStatus.PAID:
                changed_on = invoice.paid_on
                assert changed_on is not None
                date_ = format_date(changed_on.date(), format="long", locale=locale)
                return f"Payée le {date_}", "is-ok"
            if status is InvoiceStatus.CANCELLED:
                changed_on = invoice.cancelled_on
                assert changed_on is not None
                date_ = format_date(changed_on.date(), format="long", locale=locale)
                return f"Annulée le {date_}", "is-bad"

        return "", ""

    def _build_context(
        self,
        client_: schemas.Client,
        invoice: schemas.Invoice,
        company: schemas.Company,
        mode: HtmlMode,
    ) -> dict[str, Any]:
        company_address = (
            f"{company.address.address}\n{company.address.zip_code} "
            f"{company.address.city}"
        )
        client_address = (
            f"{client_.address.address}\n{client_.address.zip_code} "
            f"{client_.address.city}"
        )
        if mode is self.HtmlMode.SHOW:
            date_ = (
                invoice.created_on
                if invoice.status is InvoiceStatus.DRAFT
                else invoice.issued_on
            )
            assert date_ is not None
        else:
            date_ = (
                invoice.issued_on if invoice.issued_on is not None else datetime.now()
            )
        due_date = (
            None
            if invoice.status is InvoiceStatus.DRAFT and mode is self.HtmlMode.SHOW
            else date_ + timedelta(days=30)
        )
        stamp, tag = self._get_stamp(invoice, mode)

        locale = Config.dfacto_settings.locale
        return {
            "company": {
                "name": company.name,
                "address": company_address,
                "phone_number": company.phone_number,
                "email": company.email,
                "siret": company.siret,
                "rcs": company.rcs,
            },
            "client": {
                "name": client_.name,
                "address": client_address,
                "email": client_.email,
            },
            "invoice": {
                "code": invoice.code,
                "date": format_date(date_.date(), format="long", locale=locale),
                "due_date": None
                if due_date is None
                else format_date(due_date.date(), format="long", locale=locale),
                "raw_amount": invoice.amount.raw,
                "vat": invoice.amount.vat,
                "net_amount": invoice.amount.net,
                "stamp_text": stamp,
                "stamp_tag": tag,
                "item_list": [
                    {
                        "service": {
                            "name": item.service.name,
                            "unit_price": item.service.unit_price,
                        },
                        "quantity": item.quantity,
                        "raw_amount": item.amount.raw,
                        "vat": item.amount.vat,
                        "net_amount": item.amount.net,
                    }
                    for item in invoice.items
                ],
            },
        }

    @command
    def move_in_basket(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._back_in_basket(obj_id, invoice_id, move=True)

    @command
    def copy_in_basket(self, obj_id: int, *, invoice_id: int) -> CommandResponse:
        return self._back_in_basket(obj_id, invoice_id, move=False)

    def _back_in_basket(
        self, obj_id: int, invoice_id: int, move: bool
    ) -> CommandResponse:
        action = "move" if move else "copy"
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}_TO_BASKET-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}_TO_BASKET-INVOICE - Invoice {invoice_id} not found.",
            )
        if invoice.client_id != obj_id:
            return CommandResponse(
                CommandStatus.REJECTED,
                f"{action.upper()}_TO_BASKET-INVOICE - Invoice {invoice_id} is not "
                f"an invoice of client {obj_id}.",
            )

        try:
            if move:
                crud.invoice.move_in_basket(self.session, invoice_=invoice)
            else:
                crud.invoice.copy_in_basket(self.session, invoice_=invoice)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"{action.upper()}_TO_BASKET-INVOICE - Cannot {action} "
                f"invoice {invoice_id} of client {obj_id}: {exc}",
            )
        return CommandResponse(CommandStatus.COMPLETED)

    @command
    def revert_invoice_status(self, *, invoice_id: int) -> CommandResponse:
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
            status_log = crud.invoice.get_status_history(
                self.session, invoice_id=invoice_id
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REVERT-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REVERT-INVOICE - Invoice {invoice_id} not found.",
            )
        if len(status_log) < 2:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REVERT-INVOICE - Invoice {invoice_id} is in DRAFT status.",
            )

        current_status = invoice.status
        previous_status = status_log[-2].status
        try:
            crud.invoice.revert_status(
                self.session, invoice_=invoice, status=previous_status
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REVERT-INVOICE - Cannot revert invoice {invoice_id} from "
                f"status {current_status.name} to {previous_status.name}: {exc}",
            )
        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)

    @command
    def update_invoice_history(
        self, *, invoice_id: int, log: dict[InvoiceStatus, DatetimeRange]
    ) -> CommandResponse:
        try:
            invoice = crud.invoice.get(self.session, invoice_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE_HISTORY-INVOICE - SQL or database error: {exc}",
            )

        if invoice is None:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE_HISTORY-INVOICE - Invoice {invoice_id} not found.",
            )

        try:
            crud.invoice.set_status_history(self.session, invoice_=invoice, log=log)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"UPDATE_HISTORY-INVOICE - Cannot update history "
                f"of invoice {invoice_id} : {exc}",
            )
        body = schemas.Invoice.from_orm(invoice)
        return CommandResponse(CommandStatus.COMPLETED, body=body)


client = ClientModel()
