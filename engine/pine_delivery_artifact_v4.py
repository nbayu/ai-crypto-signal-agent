import json
from pathlib import Path


PINE_DELIVERY_DIRECTORY = Path(
    "data/pine_delivery_v4"
)


def save_pine_delivery_artifact(
    bridge_artifact,
    delivery_payload,
    *,
    directory=None,
):
    if directory is None:
        directory = PINE_DELIVERY_DIRECTORY

    directory = Path(directory)
    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    bridge_path = directory / "latest.json"
    payload_path = directory / "payload.txt"

    bridge_path.write_text(
        json.dumps(
            bridge_artifact,
            indent=2,
        )
    )
    payload_path.write_text(
        delivery_payload
    )

    return bridge_path, payload_path
