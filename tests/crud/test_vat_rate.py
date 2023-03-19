# Copyright (c) 2022, Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

from typing import cast

import pytest
import sqlalchemy as sa
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from dfacto.backend import crud, models, schemas
from tests.conftest import init_db_data

pytestmark = pytest.mark.crud


@pytest.fixture
def init_vat_rates(dbsession: Session) -> list[models.VatRate]:
    init_db_data(dbsession)

    for i in range(3):
        vat_rate = models.VatRate(
            name=f"Rate {i + 1}", rate=12.5 + 2.5 * i  # 12.5, 15, 17.5
        )
        dbsession.add(vat_rate)
        dbsession.commit()

    vat_rates = cast(
        list[models.VatRate], dbsession.scalars(sa.select(models.VatRate)).all()
    )
    return vat_rates


def test_crud_init():
    assert crud.vat_rate.model is models.VatRate


def test_crud_get_default(dbsession, init_vat_rates):
    vat_rate = crud.vat_rate.get_default(dbsession)

    assert vat_rate.is_default


def test_crud_set_default(dbsession, init_vat_rates):
    old = init_vat_rates[0]
    new = init_vat_rates[6]
    assert old.is_default
    assert not new.is_default

    crud.vat_rate.set_default(dbsession, old_default=old, new_default=new)

    assert not old.is_default
    assert new.is_default


def test_crud_set_default_error(dbsession, init_vat_rates, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    old = init_vat_rates[0]
    new = init_vat_rates[6]
    assert old.is_default
    assert not new.is_default

    with pytest.raises(crud.CrudError):
        crud.vat_rate.set_default(dbsession, old_default=old, new_default=new)

    assert old.is_default
    assert not new.is_default


def test_crud_get(dbsession, init_vat_rates):
    vat_rates = init_vat_rates

    vat_rate = crud.vat_rate.get(dbsession, vat_rates[0].id)

    assert vat_rate is vat_rates[0]


def test_crud_get_unknown(dbsession, init_vat_rates):
    vat_rates = init_vat_rates
    ids = [vr.id for vr in vat_rates]

    vat_rate = crud.vat_rate.get(dbsession, 100)

    assert 100 not in ids
    assert vat_rate is None


def test_crud_get_error(dbsession, init_vat_rates, mock_get):
    state, _called = mock_get
    state["failed"] = True

    vat_rates = init_vat_rates

    with pytest.raises(crud.CrudError):
        _vat_rate = crud.vat_rate.get(dbsession, vat_rates[0].id)


@pytest.mark.parametrize(
    "kwargs, offset, length",
    (
        ({}, 0, None),
        ({"limit": 2}, 0, 2),
        ({"skip": 2}, 2, None),
        ({"skip": 2, "limit": 2}, 2, 2),
    ),
)
def test_crud_get_multi(kwargs, offset, length, dbsession, init_vat_rates):
    vat_rates = init_vat_rates

    obj_list = crud.vat_rate.get_multi(dbsession, **kwargs)

    skip = kwargs.get("skip", 0)
    length = length or len(vat_rates) - skip
    assert len(obj_list) == length
    for i, obj in enumerate(obj_list):
        assert obj is vat_rates[i + offset]


def test_crud_get_multi_error(dbsession, init_vat_rates, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _vat_rates = crud.vat_rate.get_multi(dbsession)


def test_crud_get_all(dbsession, init_vat_rates):
    vat_rates = crud.vat_rate.get_all(dbsession)

    for i, vat_rate in enumerate(vat_rates):
        assert vat_rate is init_vat_rates[i]


def test_crud_get_all_error(dbsession, init_vat_rates, mock_select):
    state, _called = mock_select
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _vat_rates = crud.vat_rate.get_all(dbsession)


def test_crud_create(dbsession, init_vat_rates):
    vat_rate = crud.vat_rate.create(
        dbsession, obj_in=schemas.VatRateCreate(name="A new rate", rate=30.0)
    )

    assert vat_rate.id is not None
    assert vat_rate.name == "A new rate"
    assert vat_rate.rate == 30.0
    assert not vat_rate.is_default
    assert not vat_rate.is_preset
    try:
        s = dbsession.get(models.VatRate, vat_rate.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == "A new rate"
    assert s.rate == 30.0
    assert not s.is_default
    assert not s.is_preset


def test_crud_create_error(dbsession, init_vat_rates, mock_commit):
    state, _called = mock_commit
    state["failed"] = True

    with pytest.raises(crud.CrudError):
        _vat_rate = crud.vat_rate.create(
            dbsession, obj_in=schemas.VatRateCreate(name="A new rate", rate=30.0)
        )
    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )


@pytest.mark.parametrize("obj_in_factory", (schemas.VatRateUpdate, dict))
def test_crud_update(obj_in_factory, dbsession, init_vat_rates):
    vat_rate = init_vat_rates[6]

    updated = crud.vat_rate.update(
        dbsession,
        db_obj=vat_rate,
        obj_in=obj_in_factory(name="A super rate!", rate=50.0),
    )

    assert updated.id == vat_rate.id
    assert updated.name == "A super rate!"
    assert updated.rate == 50.0
    assert updated.is_default == vat_rate.is_default
    assert updated.is_preset == vat_rate.is_preset
    try:
        s = dbsession.get(models.VatRate, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == "A super rate!"
    assert s.rate == 50.0
    assert s.is_default == vat_rate.is_default
    assert s.is_preset == vat_rate.is_preset


@pytest.mark.parametrize("set_default, obj_id", ((True, 6), (False, 0)))
def test_crud_update_is_default_failed(set_default, obj_id, dbsession, init_vat_rates):
    vat_rate = init_vat_rates[obj_id]

    assert vat_rate.is_default is not set_default
    with pytest.raises(AssertionError, match="Use 'set_default' instead"):
        _updated = crud.vat_rate.update(
            dbsession,
            db_obj=vat_rate,
            obj_in=dict(name="A super rate!", rate=50.0, is_default=set_default),
        )

    try:
        s = dbsession.get(models.VatRate, vat_rate.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name is vat_rate.name
    assert s.rate == vat_rate.rate
    assert s.is_default == vat_rate.is_default
    assert s.is_preset == vat_rate.is_preset


@pytest.mark.parametrize("set_default, obj_id", ((False, 6), (True, 0)))
def test_crud_update_is_default_success(set_default, obj_id, dbsession, init_vat_rates):
    vat_rate = init_vat_rates[obj_id]

    assert vat_rate.is_default is set_default
    _updated = crud.vat_rate.update(
        dbsession, db_obj=vat_rate, obj_in=dict(is_default=set_default)
    )

    try:
        s = dbsession.get(models.VatRate, vat_rate.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name is vat_rate.name
    assert s.rate == vat_rate.rate
    assert s.is_default is set_default
    assert s.is_preset == vat_rate.is_preset


def test_crud_update_partial(dbsession, init_vat_rates):
    vat_rate = init_vat_rates[6]

    updated = crud.vat_rate.update(
        dbsession, db_obj=vat_rate, obj_in=schemas.VatRateUpdate(rate=50.0)
    )

    assert updated.id == vat_rate.id
    assert updated.name == vat_rate.name
    assert updated.rate == 50.0
    assert updated.is_default == vat_rate.is_default
    assert updated.is_preset == vat_rate.is_preset
    try:
        s = dbsession.get(models.VatRate, updated.id)
    except sa.exc.SQLAlchemyError:
        s = None
    assert s.name == vat_rate.name
    assert s.rate == 50.0
    assert s.is_default == vat_rate.is_default
    assert s.is_preset == vat_rate.is_preset


def test_crud_update_idem(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = False

    vat_rate = init_vat_rates[0]

    updated = crud.vat_rate.update(
        dbsession, db_obj=vat_rate, obj_in=schemas.VatRateUpdate(rate=vat_rate.rate)
    )

    assert updated is vat_rate
    assert len(called) == 0


def test_crud_update_error(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    vat_rate = init_vat_rates[0]

    with pytest.raises(crud.CrudError):
        _updated = crud.vat_rate.update(
            dbsession, db_obj=vat_rate, obj_in=schemas.VatRateUpdate(rate=30.0)
        )

    assert (
        dbsession.scalars(
            sa.select(models.VatRate).where(models.VatRate.rate == 30.0)
        ).first()
        is None
    )


def test_crud_delete(dbsession, init_vat_rates):
    vat_rate = init_vat_rates[0]
    assert dbsession.get(models.VatRate, vat_rate.id) is not None

    crud.vat_rate.delete(dbsession, db_obj=vat_rate)

    assert dbsession.get(models.VatRate, vat_rate.id) is None


def test_crud_delete_error(dbsession, init_vat_rates, mock_commit):
    state, called = mock_commit
    state["failed"] = True

    vat_rate = init_vat_rates[0]
    assert dbsession.get(models.VatRate, vat_rate.id) is not None

    with pytest.raises(crud.CrudError):
        crud.vat_rate.delete(dbsession, db_obj=vat_rate)

    assert dbsession.get(models.VatRate, vat_rate.id) is not None


def test_schema_from_orm(dbsession, init_vat_rates):
    vat_rate = init_vat_rates[0]

    from_db = schemas.VatRate.from_orm(vat_rate)

    assert from_db.id == vat_rate.id
    assert from_db.rate == vat_rate.rate
