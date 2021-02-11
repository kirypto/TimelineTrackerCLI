from http import HTTPStatus
from typing import Dict, Any, List

import requests


class TimelineTrackerGateway:
    _url: str

    def __init__(self, url: str):
        self._url = url

    def post_location(self, location_json: Dict[str, Any]) -> Dict[str, Any]:
        url = f"{self._url}/api/location"
        response = requests.post(url, json=location_json)
        if response.status_code != HTTPStatus.CREATED:
            raise RuntimeError(f"Failed to post location: {response.text}")
        return response.json()

    def get_location(self, location_id: str) -> Dict[str, Any]:
        url = f"{self._url}/api/location/{location_id}"
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to get location: {response.text}")
        return response.json()

    def patch_location(self, location_id: str, patches: List[dict]) -> Dict[str, Any]:
        url = f"{self._url}/api/location/{location_id}"
        response = requests.patch(url, json=patches)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to patch location: {response.text}")
        return response.json()

    def get_locations(self, **filter_kwargs: Dict[str, str]) -> List[str]:
        url = f"{self._url}/api/locations"
        if filter_kwargs:
            url += "?"
            url += "&".join([f"{key}={val}" for key, val in filter_kwargs.items()])
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to get locations: {response.text}")
        return response.json()


