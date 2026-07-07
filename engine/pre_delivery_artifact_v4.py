import json
from pathlib import Path


PRE_DELIVERY_DIRECTORY = Path(
    "data/pre_delivery_v4"
)
PRE_DELIVERY_FILENAME = "latest.json"


def serialize_artifact_value(value):
    isoformat = getattr(
        value,
        "isoformat",
        None,
    )

    if callable(isoformat):
        return isoformat()

    return str(value)


def save_pre_delivery_artifact(artifact):
    PRE_DELIVERY_DIRECTORY.mkdir(
        parents=True,
        exist_ok=True,
    )

    path = (
        PRE_DELIVERY_DIRECTORY
        / PRE_DELIVERY_FILENAME
    )

    path.write_text(
        json.dumps(
            artifact,
            indent=2,
            default=serialize_artifact_value,
        )
    )

    return path
