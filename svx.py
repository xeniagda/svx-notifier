from __future__ import annotations

from typing import Callable, Awaitable, List, NewType, Optional, Dict
import sys

from abc import ABC
import asyncio
import aiohttp
import traceback
from datetime import datetime
import log

import time

import logging

SVX_LOG = logging.getLogger("svx")

TalkGroup = NewType("TalkGroup", int)

DATA_ENDPOINT = "https://svxportal.sm2ampr.net/reflectorproxy/"
TIME_FOR_NOTIFICATION = 10 * 60  # seconds


class Node:
    def __init__(
        self,
        name: str,  # key
        location: str,  # nodeLocation
        monitoring_talkgroups: List[TalkGroup],  # monitoredTGs
        is_talking: bool,  # isTalker
        talk_group: Optional[int],  # tg
        talkgroup_tones: Optional[Dict[TalkGroup, str]],  # ¬toneToTalkgroup
    ):
        self.name = name
        self.location = location
        self.monitoring_talkgroups = monitoring_talkgroups
        self.is_talking = is_talking
        self.talk_group = talk_group
        self.talkgroup_tones = talkgroup_tones

    @staticmethod
    def from_json_obj(name: str, obj: Dict[str, object]) -> Node:
        assert "nodeLocation" in obj or "NodeLocation" in obj
        location = obj.get("nodeLocation", obj.get("NodeLocation", None))
        assert isinstance(location, str)

        assert "monitoredTGs" in obj
        monitoring_talkgroups_ints = obj["monitoredTGs"]
        assert isinstance(monitoring_talkgroups_ints, list)
        assert all(isinstance(x, int) for x in monitoring_talkgroups_ints)
        monitoring_talkgroups = [TalkGroup(x) for x in monitoring_talkgroups_ints]

        assert "isTalker" in obj
        is_talking = obj["isTalker"]
        assert isinstance(is_talking, bool)

        assert "tg" in obj
        assert isinstance(obj["tg"], int)
        talk_group = TalkGroup(obj["tg"]) if obj["tg"] != 0 else None

        talkgroup_tones = {}
        if "toneToTalkgroup" in obj:
            tttg = obj["toneToTalkgroup"]
            assert isinstance(tttg, dict)
            for freq_str, tg_int in tttg.items():
                assert isinstance(freq_str, str)
                assert isinstance(tg_int, int)
                tg = TalkGroup(tg_int)
                talkgroup_tones[tg] = freq_str

        return Node(
            name=name,
            location=location,
            monitoring_talkgroups=monitoring_talkgroups,
            is_talking=is_talking,
            talk_group=talk_group,
            talkgroup_tones=talkgroup_tones,
        )

    def __str__(self):
        return ("Node("
            + f"name={self.name!r}"
            + f", location={self.location!r}"
            + f", monitoring_talkgroups={self.monitoring_talkgroups!r}"
            + f", is_talking={self.is_talking!r}"
            + f", talk_group={self.talk_group!r}"
            + f", talkgroup_tones={self.talkgroup_tones!r}"
            + ")"
        )

    __repr__ = __str__


class SVXNotifier:
    def __init__(
        self,
        connection: aiohttp.ClientSession,
    ):
        self.callbacks: List[Callable[[Node, Optional[float]], Awaitable[None]]] = []
        self.connection = connection

        self.node_last_active: Dict[str, float] = {}  # {name: ts}

    def add_callback(self, on_update: Callable[[Node, Optional[float]], Awaitable[None]]):  # on_update: (node, last_active_time) -> ...
        self.callbacks.append(on_update)

    async def poll(self):
        SVX_LOG.debug("Polling")

        start = time.time()
        data = await self.connection.get(
            DATA_ENDPOINT,
        )

        data_json = await data.json(content_type="text/html")  # smh smh smh
        if data_json is None:
            SVX_LOG.warning("No JSON recieved!")
            return

        req_time = time.time() - start
        SVX_LOG.debug(f"Request took {req_time}")

        if "nodes" not in data_json:
            SVX_LOG.warning("No nodes in data")
            return

        nodes = data_json["nodes"]
        if not isinstance(nodes, dict):
            SVX_LOG.warning("nodes is not dict")
            return

        for node_name, node_info in nodes.items():
            if "hidden" in node_info and node_info["hidden"]:
                continue

            try:
                node = Node.from_json_obj(node_name, node_info)
            except AssertionError as e:
                SVX_LOG.error(f"Error loading {node_name}")
                SVX_LOG.error(e, exc_info=True)
                SVX_LOG.error(f"Data: {node_info!r}")
            else:
                if node.is_talking:
                    await self.node_active(node)

    async def node_active(self, node: Node):
        SVX_LOG.debug(f"Node activate: {node!r}")
        last_active_time = self.node_last_active.get(node.name, None)

        now = time.time()
        time_since = now - last_active_time if last_active_time is not None else None

        if time_since is None or time_since > TIME_FOR_NOTIFICATION:
            SVX_LOG.info(f"Node activated: {node!r}")
            await asyncio.gather(*[callback(node, time_since) for callback in self.callbacks])

        self.node_last_active[node.name] = now

    async def poll_periodically(self):
        SVX_LOG.info("Starting periodic check")
        while True:
            try:
                await self.poll()
            except KeyboardInterrupt as e:
                SVX_LOG.error(e, exc_info=True)
                break
            except Exception as e:
                SVX_LOG.error(e, exc_info=True)

            await asyncio.sleep(1)


if __name__ == "__main__":
    async def test_notifier():
        async with aiohttp.ClientSession() as sess:
            HANDLER_LOG = logging.getLogger("handler")
            async def on_active(node: Node, time_since: Optional[float]):
                now = datetime.now()
                HANDLER_LOG.info(f"Node {node.name} activated at {now.isoformat()}! First time in {time_since} seconds")
                sys.stdout.flush()

            notifier = SVXNotifier(sess)
            notifier.add_callback(on_active)

            await notifier.poll_periodically()

    asyncio.run(test_notifier())
