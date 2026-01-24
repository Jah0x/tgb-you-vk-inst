from __future__ import annotations

from typing import Annotated

from dataclasses import asdict

from fastapi import FastAPI, HTTPException, Path, status
from pydantic import BaseModel, Field

from shared.config import load_settings
from shared.services import (
    add_accounts,
    add_accounts_to_grid,
    create_grid,
    delete_account,
    delete_grid,
    list_accounts,
    list_grids,
    run_grid,
)
from shared.services.errors import ConflictError, NotFoundError, ServiceError, ValidationError
from shared.storage import Storage, init_db

app = FastAPI(title="tgb-you-vk API")

settings = load_settings()
init_db(settings.db_url)
store = Storage(settings.db_url)


class AccountCreateRequest(BaseModel):
    names: list[str] = Field(..., min_length=1)


class GridCreateRequest(BaseModel):
    name: str = Field(..., min_length=1)


class GridAccountsRequest(BaseModel):
    accounts: str | list[str]


class AccountListResponseModel(BaseModel):
    accounts: list[str]


class AccountAddResponseModel(BaseModel):
    added: list[str]
    skipped: list[str]


class GridInfoModel(BaseModel):
    name: str
    accounts: list[str]


class GridListResponseModel(BaseModel):
    grids: list[GridInfoModel]


class GridCreateResponseModel(BaseModel):
    name: str


class GridAccountsResponseModel(BaseModel):
    added: list[str]
    skipped: list[str]


def _handle_service_error(exc: ServiceError) -> None:
    if isinstance(exc, ValidationError):
        status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
    elif isinstance(exc, ConflictError):
        status_code = status.HTTP_409_CONFLICT
    elif isinstance(exc, NotFoundError):
        status_code = status.HTTP_404_NOT_FOUND
    else:
        status_code = status.HTTP_400_BAD_REQUEST
    detail = {"message": exc.message, "details": exc.details}
    raise HTTPException(status_code=status_code, detail=detail)


def _format_accounts_payload(payload: GridAccountsRequest) -> str:
    if isinstance(payload.accounts, str):
        return payload.accounts
    return ",".join(payload.accounts)


@app.get("/accounts/{chat_id}", response_model=AccountListResponseModel)
def api_list_accounts(chat_id: Annotated[int, Path(..., ge=1)]) -> AccountListResponseModel:
    result = list_accounts(store, chat_id)
    return AccountListResponseModel(**asdict(result))


@app.post("/accounts/{chat_id}", response_model=AccountAddResponseModel)
def api_add_accounts(
    chat_id: Annotated[int, Path(..., ge=1)], payload: AccountCreateRequest
) -> AccountAddResponseModel:
    try:
        result = add_accounts(store, chat_id, payload.names)
        return AccountAddResponseModel(**asdict(result))
    except ServiceError as exc:
        _handle_service_error(exc)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/accounts/{chat_id}/{name}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_account(
    chat_id: Annotated[int, Path(..., ge=1)], name: str
) -> None:
    try:
        delete_account(store, chat_id, name)
    except ServiceError as exc:
        _handle_service_error(exc)


@app.get("/grids/{chat_id}", response_model=GridListResponseModel)
def api_list_grids(chat_id: Annotated[int, Path(..., ge=1)]) -> GridListResponseModel:
    result = list_grids(store, chat_id)
    return GridListResponseModel(**asdict(result))


@app.post("/grids/{chat_id}", response_model=GridCreateResponseModel)
def api_create_grid(
    chat_id: Annotated[int, Path(..., ge=1)], payload: GridCreateRequest
) -> GridCreateResponseModel:
    try:
        result = create_grid(store, chat_id, payload.name)
        return GridCreateResponseModel(**asdict(result))
    except ServiceError as exc:
        _handle_service_error(exc)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.delete("/grids/{chat_id}/{name}", status_code=status.HTTP_204_NO_CONTENT)
def api_delete_grid(
    chat_id: Annotated[int, Path(..., ge=1)], name: str
) -> None:
    try:
        delete_grid(store, chat_id, name)
    except ServiceError as exc:
        _handle_service_error(exc)


@app.post(
    "/grids/{chat_id}/{grid_name}/accounts", response_model=GridAccountsResponseModel
)
def api_add_grid_accounts(
    chat_id: Annotated[int, Path(..., ge=1)],
    grid_name: str,
    payload: GridAccountsRequest,
) -> GridAccountsResponseModel:
    raw_accounts = _format_accounts_payload(payload)
    try:
        result = add_accounts_to_grid(store, chat_id, grid_name, raw_accounts)
        return GridAccountsResponseModel(**asdict(result))
    except ServiceError as exc:
        _handle_service_error(exc)
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@app.post("/grids/{chat_id}/{grid_name}/run")
def api_run_grid(
    chat_id: Annotated[int, Path(..., ge=1)],
    grid_name: str,
    payload: GridAccountsRequest,
) -> dict[str, list[str]]:
    raw_accounts = _format_accounts_payload(payload)
    try:
        accounts = run_grid(store, chat_id, grid_name, raw_accounts)
    except ServiceError as exc:
        _handle_service_error(exc)
    return {"accounts": accounts}
