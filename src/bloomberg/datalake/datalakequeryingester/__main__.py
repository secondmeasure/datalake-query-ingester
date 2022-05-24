"""
 ** Copyright 2021 Bloomberg Finance L.P.
 **
 ** Licensed under the Apache License, Version 2.0 (the "License");
 ** you may not use this file except in compliance with the License.
 ** You may obtain a copy of the License at
 **
 **     http://www.apache.org/licenses/LICENSE-2.0
 **
 ** Unless required by applicable law or agreed to in writing, software
 ** distributed under the License is distributed on an "AS IS" BASIS,
 ** WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 ** See the License for the specific language governing permissions and
 ** limitations under the License.
"""


from __future__ import annotations

import json
import logging
from typing import Any, cast

import uvicorn
from fastapi import FastAPI, Request
from fastapi.params import Depends
from fastapi.responses import PlainTextResponse
from fastapi.security import APIKeyHeader

from ._data_models import HealthyResponse
from ._request_handler import add_query_ingest_impl

app = FastAPI()

X_API_KEY = Depends(APIKeyHeader(name="X-API-Key", auto_error=False))


@app.get("/healthy", response_model=HealthyResponse)
async def healthy() -> HealthyResponse:
    return HealthyResponse(message="healthy")


@app.post("/add_query_ingest")
async def add_query_ingest(request: Request, x_api_key: Any = X_API_KEY) -> dict[str, bool]:
    request_body = await request.body()
    logging.debug(f"Received request {str(request_body)}")

    # Remove info in request that is not used by consumer to reduce request size
    request_body = json.loads(request_body.decode("utf-8"))
    request_body.get("metadata", {}).pop("payload", None)
    request_body.get("ioMetadata", {}).pop("connectorInfo", None)
    request_body.get("statistics", {}).pop("operatorSummaries", None)
    request_body = json.dumps(request_body).encode("utf-8")
    logging.info(f"Pruned request {str(request_body)}")

    return {"ok": add_query_ingest_impl(cast(str, x_api_key), request_body)}


@app.exception_handler(Exception)
async def validation_exception_handler(_request: Request, exc: Exception) -> PlainTextResponse:
    logging.exception("Exception in requests: ", exc)
    return PlainTextResponse("Something went wrong", status_code=500)


if __name__ == "__main__":
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8080,
        workers=1,
        log_config="/opt/config/datalakequeryingester/log_config.yaml",
    )
