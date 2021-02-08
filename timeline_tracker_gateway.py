from http import HTTPStatus
from typing import Dict, Any

import requests


class TimelineTrackerGateway:
    _url: str

    def __init__(self, url: str):
        self._url = url

    def post_location(self, location_id: str, location_json: Dict[str, Any]) -> None:
        url = f"{self._url}/api/location/{location_id}"
        response = requests.post(url, json=location_json)
        if response.status_code != HTTPStatus.CREATED:
            raise RuntimeError(f"Failed to post location: {response.text}")

    def get_location(self, location_id: str) -> Dict[str, Any]:
        url = f"{self._url}/api/location/{location_id}"
        response = requests.get(url)
        if response.status_code != HTTPStatus.OK:
            raise RuntimeError(f"Failed to post location: {response.text}")
        return response.json()

