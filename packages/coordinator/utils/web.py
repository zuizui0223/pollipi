import asyncio
from abc import ABC, abstractmethod
from typing import Any, Iterable, Tuple, Optional

from starlette.websockets import WebSocketState, WebSocket, WebSocketDisconnect


class EventBasedWebSocketHandler(ABC):

    @property
    def socket(self) -> WebSocket:
        return self.__socket

    def __init__(self, websocket: WebSocket):
        if not isinstance(websocket, WebSocket):
            raise TypeError(
                f"Wrong argument type for argument 'websocket'. expected Websocket, got {type(websocket)}"
            )
        self.__socket = websocket

    def __call__(self, *args, **kwargs) -> Any:
        self.work_task = asyncio.create_task(self.work(*args, **kwargs))
        def _on_done(task: asyncio.Task[Any]):
            try:
                loop = asyncio.get_running_loop()
                loop.create_task(self.close())
            except Exception:
                pass
        self.work_task.add_done_callback(_on_done)

    async def work(self, *args, **kwargs):

        # handle event in connecting
        try:
            await self.on_connect(*args, **kwargs)
            if self.socket.application_state == WebSocketState.DISCONNECTED:
                return
            elif self.socket.application_state == WebSocketState.CONNECTING:
                # the user didn't call either of `accept()` or `close()`
                await self.socket.accept()
        except Exception as e:
            await self.on_exception(e)

        # main message loop
        try:
            while True:
                # receive message
                code = -1
                message = {}
                if self.socket.client_state != WebSocketState.DISCONNECTED:
                    message = await self.socket.receive()
                    code = message.get("code", -1)

                # if disconnected, call the handler
                if self.socket.client_state == WebSocketState.DISCONNECTED:
                    await self.on_disconnect(code)
                    break
                # else call receive handler
                else:
                    await self.on_receive(
                        message.get("text", None), message.get("bytes", None)
                    )

        except WebSocketDisconnect as d:
            await self.on_disconnect(d.code, d.reason)
        except Exception as e:
            await self.on_exception(e)

        finally:
            await self.close()

    @abstractmethod
    async def on_connect(self, *args, **kwargs) -> None:
        pass

    @abstractmethod
    async def on_receive(self, text: Optional[str], bytes: Optional[bytes]) -> None:
        pass

    @abstractmethod
    async def on_disconnect(self, code: int = -1, reason: Optional[Any] = None) -> None:
        pass

    async def on_exception(self, e: Exception) -> None:
        await self.close()
        raise e

    async def send(self, data: Any, json_mode: str = "text") -> None:
        if isinstance(data, str):
            await self.socket.send_text(data)
        elif isinstance(data, bytes):
            await self.socket.send_bytes(data)
        else:
            await self.socket.send_json(data, mode=json_mode)

    async def accept(
        self,
        subprotocol: Optional[str] = None,
        headers: Optional[Iterable[Tuple[bytes, bytes]]] = None,
    ):
        await self.socket.accept(subprotocol=subprotocol, headers=headers)

    async def close(self, code: int = 1000, reason: Optional[str] = None):
        if (
            self.socket.application_state != WebSocketState.DISCONNECTED
            and self.socket.client_state != WebSocketState.DISCONNECTED
        ):
            await self.socket.close(code, reason)
