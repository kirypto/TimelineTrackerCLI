from http import HTTPStatus
from typing import Dict, Any, List, Union

import requests

from cache import Cache, with_cache


class TimelineTrackerGateway:
    _url: str

    def __init__(self, url: str):
        self._url = url
        self._cache = Cache("TimelineTrackerGateway", file=True)

    def post_entity(self, resource: str, entity_json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._url}/api/{resource}"
        response = requests.post(url, json=entity_json)
        if response.status_code != HTTPStatus.CREATED:
            raise RuntimeError(f"Failed to post entity: {response.text}")
        return response.json()

    def get_entity(self, resource: str, entity_id: str) -> Dict[str, Any]:
        return self._cache.get2(self._inner_get_entity, resource, entity_id)

    def patch_entity(self, resource: str, entity_id: str, patches: List[dict]) -> Dict[str, Any]:
        url = f"{self._url}/api/{resource}/{entity_id}"
        response = requests.patch(url, json=patches)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to patch entity: {response.text}")
        self._cache.invalidate(self._inner_get_entity, resource, entity_id)
        return response.json()

    def get_entities(self, resource: str, **filter_kwargs: Dict[str, str]) -> List[str]:
        url = f"{self._url}/api/{resource}s"
        if filter_kwargs:
            url += "?"
            url += "&".join([f"{key}={val}" for key, val in filter_kwargs.items()])
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to get entities: {response.text}")
        return response.json()

    def get_timeline(self, resource: str, entity_id: str, **filter_kwargs: Dict[str, str]) -> List[Union[str, dict]]:
        url = f"{self._url}/api/{resource}/{entity_id}/timeline"
        if filter_kwargs:
            url += "?"
            url += "&".join([f"{key}={val}" for key, val in filter_kwargs.items()])
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to get timeline: {response.text}")
        return response.json()

    def _inner_get_entity(self, resource: str, entity_id: str) -> Dict[str, Any]:
        url = f"{self._url}/api/{resource}/{entity_id}"
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to get entity: {response.text}")
        return response.json()
