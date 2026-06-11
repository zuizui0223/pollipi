from __future__ import annotations

from typing import Any, Optional

import httpx
from fastapi import Depends, HTTPException, Query
from fastapi.responses import Response, StreamingResponse

from base import app
from constants import Token
from devices.pi_client import PiClient
from devices.schemas import (
    DeviceCreateRequest,
    DeviceListResponse,
    DeviceResponse,
    DeviceUpdateRequest,
)
from devices.service import (
    create_device,
    delete_device,
    get_device,
    list_devices,
    refresh_device_status,
    to_response,
    update_device,
)
from user.auth import CurrentUser
from user.model import User


@app.get("/api/devices", response_model=DeviceListResponse)
async def api_list_devices(user: User = Depends(CurrentUser(Token.Access.General))) -> DeviceListResponse:
    return DeviceListResponse(devices=await list_devices(user.id))


@app.post("/api/devices", response_model=DeviceResponse)
async def api_create_device(
    request: DeviceCreateRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> DeviceResponse:
    return await create_device(user.id, request)


@app.get("/api/devices/{device_id}", response_model=DeviceResponse)
async def api_get_device(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> DeviceResponse:
    return to_response(await get_device(user.id, device_id))


@app.patch("/api/devices/{device_id}", response_model=DeviceResponse)
async def api_update_device(
    device_id: int,
    request: DeviceUpdateRequest,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> DeviceResponse:
    return await update_device(user.id, device_id, request)


@app.delete("/api/devices/{device_id}", status_code=204)
async def api_delete_device(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    await delete_device(user.id, device_id)
    return Response(status_code=204)


@app.get("/api/devices/{device_id}/device")
async def api_proxy_device(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("GET", "/device")


@app.get("/api/devices/{device_id}/status")
async def api_proxy_status(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    return await refresh_device_status(user.id, device_id)


@app.get("/api/devices/{device_id}/system")
async def api_proxy_system(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("GET", "/system")


@app.post("/api/devices/{device_id}/start")
async def api_proxy_start(
    device_id: int,
    request: dict[str, Any],
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url, timeout=15).json("POST", "/start", body=request)


@app.post("/api/devices/{device_id}/stop")
async def api_proxy_stop(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url, timeout=15).json("POST", "/stop")


@app.get("/api/devices/{device_id}/images")
async def api_proxy_images(
    device_id: int,
    limit: int = Query(default=40, ge=1, le=200),
    collection: str = Query(default="all"),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json(
        "GET",
        "/images",
        params={"limit": limit, "collection": collection},
    )


@app.delete("/api/devices/{device_id}/images")
async def api_proxy_delete_all_images(
    device_id: int,
    request: dict[str, Any],
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("DELETE", "/images", body=request)


@app.post("/api/devices/{device_id}/images/{filename}/label")
async def api_proxy_label_image(
    device_id: int,
    filename: str,
    request: dict[str, Any],
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("POST", f"/images/{filename}/label", body=request)


@app.delete("/api/devices/{device_id}/images/{filename}")
async def api_proxy_delete_image(
    device_id: int,
    filename: str,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("DELETE", f"/images/{filename}")


@app.get("/api/devices/{device_id}/images/{filename}")
async def api_proxy_image_file(
    device_id: int,
    filename: str,
    collection: str = Query(default="all"),
    download: bool = Query(default=False),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    device = await get_device(user.id, device_id)
    content, media_type, disposition = await PiClient(device.base_url, timeout=30).bytes(
        "GET",
        f"/images/{filename}",
        params={"collection": collection, "download": download},
    )
    headers = {"Cache-Control": "no-store"}
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(content=content, media_type=media_type, headers=headers)


@app.get("/api/devices/{device_id}/latest")
async def api_proxy_latest(
    device_id: int,
    capture: Optional[str] = Query(default=None),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    device = await get_device(user.id, device_id)
    content, media_type, disposition = await PiClient(device.base_url, timeout=30).bytes(
        "GET",
        "/latest",
        params={"capture": capture} if capture else None,
    )
    headers = {"Cache-Control": "no-store"}
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(content=content, media_type=media_type, headers=headers)


@app.get("/api/devices/{device_id}/preview")
async def api_proxy_preview(
    device_id: int,
    t: Optional[str] = Query(default=None),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    device = await get_device(user.id, device_id)
    content, media_type, _ = await PiClient(device.base_url, timeout=30).bytes(
        "GET",
        "/preview",
        params={"t": t} if t else None,
    )
    return Response(content=content, media_type=media_type, headers={"Cache-Control": "no-store"})


@app.get("/api/devices/{device_id}/mjpeg")
async def api_proxy_mjpeg(
    device_id: int,
    detect: bool = Query(default=False),
    t: Optional[str] = Query(default=None),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> StreamingResponse:
    device = await get_device(user.id, device_id)
    client = httpx.AsyncClient(timeout=None)
    request = client.build_request(
        "GET",
        f"{device.base_url.rstrip('/')}/mjpeg",
        params={"detect": detect, "t": t},
    )
    response = await client.send(request, stream=True)
    if response.status_code >= 400:
        body = await response.aread()
        await response.aclose()
        await client.aclose()
        raise HTTPException(status_code=response.status_code, detail=body.decode("utf-8", errors="replace"))

    async def iterator():
        try:
            async for chunk in response.aiter_bytes():
                yield chunk
        finally:
            await response.aclose()
            await client.aclose()

    return StreamingResponse(
        iterator(),
        media_type=response.headers.get("content-type", "multipart/x-mixed-replace; boundary=frame"),
        headers={"Cache-Control": "no-store"},
    )


@app.get("/api/devices/{device_id}/exports/images.zip")
async def api_proxy_images_zip(
    device_id: int,
    collection: str = Query(default="all"),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    device = await get_device(user.id, device_id)
    content, media_type, disposition = await PiClient(device.base_url, timeout=60).bytes(
        "GET",
        "/exports/images.zip",
        params={"collection": collection},
    )
    headers = {}
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(content=content, media_type=media_type, headers=headers)


@app.get("/api/devices/{device_id}/events")
async def api_proxy_events(
    device_id: int,
    limit: int = Query(default=80, ge=1, le=500),
    category: str = Query(default="all"),
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json(
        "GET",
        "/events",
        params={"limit": limit, "category": category},
    )


@app.post("/api/devices/{device_id}/events/{event_id}/label")
async def api_proxy_event_label(
    device_id: int,
    event_id: str,
    request: dict[str, Any],
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("POST", f"/events/{event_id}/label", body=request)


@app.get("/api/devices/{device_id}/events/export_labels.csv")
async def api_proxy_event_labels_csv(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Response:
    device = await get_device(user.id, device_id)
    content, media_type, disposition = await PiClient(device.base_url, timeout=30).bytes(
        "GET",
        "/events/export_labels.csv",
    )
    headers = {}
    if disposition:
        headers["Content-Disposition"] = disposition
    return Response(content=content, media_type=media_type, headers=headers)


@app.get("/api/devices/{device_id}/training/status")
async def api_proxy_training_status(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url).json("GET", "/training/status")


@app.post("/api/devices/{device_id}/training/start")
async def api_proxy_training_start(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url, timeout=60).json("POST", "/training/start")


@app.delete("/api/devices/{device_id}/training/model")
async def api_proxy_training_reset(
    device_id: int,
    user: User = Depends(CurrentUser(Token.Access.General)),
) -> Any:
    device = await get_device(user.id, device_id)
    return await PiClient(device.base_url, timeout=30).json("DELETE", "/training/model")
