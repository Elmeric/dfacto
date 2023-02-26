# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass
from typing import Type, Optional

from dfacto.models.util import Period, PeriodFilter
from dfacto.models import db, crud, schemas
from dfacto.models.models import InvoiceStatus
from dfacto.models.api.command import CommandResponse, CommandStatus
from .base import DFactoModel


@dataclass()
class ClientModel(DFactoModel[crud.CRUDClient, schemas.Client]):
    crud_object: crud.CRUDClient = crud.client
    schema: Type[schemas.Client] = schemas.Client

    def get_active(self) -> CommandResponse:
        try:
            clients = self.crud_object.get_active(self.Session)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-ACTIVE - SQL or database error: {exc}",
            )
        else:
            body = [schemas.Client.from_orm(client_) for client_ in clients]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_basket(self, obj_id: int) -> CommandResponse:
        try:
            db_obj = self.crud_object.get_basket(self.Session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-BASKET - SQL or database error: {exc}",
            )
        else:
            if db_obj is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"GET-BASKET - Basket of client {obj_id} not found.",
                )
            else:
                body = schemas.Basket.from_orm(db_obj)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    def get_invoices(
        self,
        obj_id: int,    # client id
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
            period = Period()   # i.e. from now to the epoch
        if status is not None:
            return self._get_invoices_by_status(obj_id, status=status, period=period)
        else:
            return self._get_invoices(obj_id, period=period)

    def _get_invoices_by_status(self, obj_id: int, *, status: InvoiceStatus, period: Period):
        try:
            invoices = self.crud_object.get_invoices_by_status(
                self.Session, obj_id, status=status, period=period
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICES - SQL or database error: {exc}",
            )
        else:
            body = [schemas.Invoice.from_orm(invoice) for invoice in invoices]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def _get_invoices(self, obj_id: int, *, period: Period):
        try:
            invoices = self.crud_object.get_invoices(self.Session, obj_id, period=period)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"GET-INVOICES - SQL or database error: {exc}",
            )
        else:
            body = [schemas.Invoice.from_orm(invoice) for invoice in invoices]
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def rename(self, obj_id: int, name: str) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(name=name))

    def change_address(self, obj_id: int, address: schemas.Address) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(address=address))

    def set_active(self, obj_id: int) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(is_active=True))

    def set_inactive(self, obj_id: int) -> CommandResponse:
        return self.update(obj_id, obj_in=schemas.ClientUpdate(is_active=False))

    def delete(self, obj_id: int) -> CommandResponse:
        try:
            client_ = self.crud_object.get(self.Session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"DELETE - SQL or database error: {exc}",
            )
        else:
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

            if len(client_.basket.items) > 0:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    f"DELETE - Client {client_.name} has a non-empty basket"
                    f" and cannot be deleted.",
                )

            try:
                self.crud_object.delete(self.Session, db_obj=client_)
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"DELETE - Cannot delete object {obj_id}: {exc}",
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)

    def add_to_basket(
        self, obj_id: int, *, service_id: int, quantity: int = 1
    ) -> CommandResponse:
        try:
            basket = self.crud_object.get_basket(self.Session, obj_id)
            service = crud.service.get(self.Session, service_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"ADD-TO-BASKET - SQL or database error: {exc}",
            )
        else:
            if basket is None or service is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"ADD-TO-BASKET - Client {obj_id} or "
                    f"service {service_id} not found.",
                )

            try:
                it = self.crud_object.add_to_basket(
                    self.Session, basket=basket, service=service, quantity=quantity
                )
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"ADD-TO-BASKET - Cannot add to basket of client {obj_id}: {exc}",
                )
            else:
                body = schemas.Item.from_orm(it)
                return CommandResponse(CommandStatus.COMPLETED, body=body)

    def update_item_quantity(self, item_id: int, *, quantity: int) -> CommandResponse:
        if quantity <= 0:
            return CommandResponse(
                CommandStatus.REJECTED,
                "UPDATE-ITEM - Item quantity shall be at least one.",
            )

        try:
            item = crud.item.get(self.Session, item_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"BASKET-UPDATE-ITEM - SQL or database error: {exc}",
            )
        else:
            if item is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"BASKET-UPDATE-ITEM - Item {item_id} not found.",
                )

            invoice = item.invoice
            if invoice is not None and invoice.status != InvoiceStatus.DRAFT:
                return CommandResponse(
                    CommandStatus.REJECTED,
                    "BASKET-UPDATE-ITEM - Cannot change items of a non-draft invoice.",
                )

            try:
                self.crud_object.update_item_quantity(
                    self.Session, db_obj=item, quantity=quantity
                )
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"BASKET-UPDATE-ITEM - Cannot remove item {item_id}: {exc}",
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)

    def remove_from_basket(self, item_id: int) -> CommandResponse:
        try:
            item = crud.item.get(self.Session, item_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"REMOVE-FROM-BASKET - SQL or database error: {exc}",
            )
        else:
            if item is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"REMOVE-FROM-BASKET - Item {item_id} not found.",
                )

            try:
                self.crud_object.remove_from_basket(self.Session, db_obj=item)
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"REMOVE-FROM-BASKET - Cannot remove item {item_id}: {exc}",
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)

    def clear_basket(self, obj_id: int) -> CommandResponse:
        try:
            basket = self.crud_object.get_basket(self.Session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CLEAR-BASKET - SQL or database error: {exc}",
            )
        else:
            if basket is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"CLEAR-BASKET - Basket of client {obj_id} not found.",
                )

            try:
                self.crud_object.clear_basket(self.Session, db_obj=basket)
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"CLEAR-BASKET - Cannot clear basket of client {obj_id}: {exc}",
                )
            else:
                return CommandResponse(CommandStatus.COMPLETED)

    # TODO:
    # create_invoice (create empty invoice)
    # create_from_basket
    # add_item, update_item_quantity, remove_item, clear (if draft)
    # mark_as: emitted, paid, reminded, cancelled
    # delete (if draft)
    # get: by status, for a period of time

    def create_invoice(self, obj_id: int) -> CommandResponse:
        try:
            db_obj = crud.invoice.create(
                self.Session, obj_in=schemas.InvoiceCreate(obj_id)
            )
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE-INVOICE - Cannot create an invoice for client {obj_id}: {exc}",
            )
        else:
            body = self.schema.from_orm(db_obj)
            return CommandResponse(CommandStatus.COMPLETED, body=body)

    def invoice_from_basket(
        self, obj_id: int, clear_basket: bool = True
    ) -> CommandResponse:
        try:
            basket = crud.client.get_basket(self.Session, obj_id)
        except crud.CrudError as exc:
            return CommandResponse(
                CommandStatus.FAILED,
                f"CREATE-FROM-BASKET - SQL or database error: {exc}",
            )
        else:
            if basket is None:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"CREATE_FROM-BASKET - Basket of client {obj_id} not found.",
                )
            if len(basket.items) <= 0:
                # No items in basket of client: create an empty invoice
                return self.create_invoice(obj_id)

            try:
                inv = crud.invoice.invoice_from_basket(
                    self.Session, basket, clear_basket=clear_basket
                )
            except crud.CrudError as exc:
                return CommandResponse(
                    CommandStatus.FAILED,
                    f"CREATE_FROM-BASKET - Cannot create invoice from basket of client "
                    f"{obj_id}: {exc}",
                )
            else:
                body = schemas.Invoice.from_orm(inv)
                return CommandResponse(CommandStatus.COMPLETED, body=body)


client = ClientModel(db.Session)
