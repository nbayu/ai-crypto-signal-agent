"""Pure, transport-independent Telegram command application for Phase 05."""

from dataclasses import dataclass

from engine.quota_slot_engine_v4 import QuotaSlotRejected


TRUNCATION_MARKER = "\n[truncated]"


@dataclass(frozen=True)
class TelegramCommandRequest:
    command: object
    telegram_user_id: object
    chat_id: object = None
    arguments: object = ()


@dataclass(frozen=True)
class TelegramApplicationResponse:
    category: str
    command: str
    message: str
    scan: object = None


class _WorkerFailureMarker(Exception):
    def __init__(self, original_worker_error):
        self._original_worker_error = original_worker_error
        super().__init__("worker execution failed")


def map_telegram_user_to_subject_id(telegram_user_id):
    """Map a positive immutable Telegram user identifier to a quota subject."""
    if type(telegram_user_id) is not int or telegram_user_id <= 0:
        raise ValueError("telegram_user_id must be a positive integer")
    return f"telegram:user:{telegram_user_id}"


class TelegramApplicationV4:
    def __init__(
        self,
        *,
        window_id_provider,
        quota_limit,
        slot_capacity,
        quota_state_path,
        worker_state_path,
        quota_now_provider,
        reservation_id_provider,
        quota_slot_worker,
        worker,
        max_response_chars,
    ):
        self._window_id_provider = window_id_provider
        self._quota_limit = quota_limit
        self._slot_capacity = slot_capacity
        self._quota_state_path = quota_state_path
        self._worker_state_path = worker_state_path
        self._quota_now_provider = quota_now_provider
        self._reservation_id_provider = reservation_id_provider
        self._quota_slot_worker = quota_slot_worker
        self._worker = worker
        self._max_response_chars = max_response_chars

    def dispatch(self, request):
        command = self._command_from_request(request)
        if command not in {"/start", "/help", "/status", "/scan"}:
            return self._response(
                "INVALID_INPUT",
                command,
                "Command or request cannot be processed.",
            )

        if command == "/start":
            return self._response(
                "INFO",
                command,
                "Telegram scan interface ready. Use /help for commands.",
            )
        if command == "/help":
            return self._response(
                "INFO",
                command,
                "Available commands: /start /help /status /scan",
            )
        if command == "/status":
            return self._status_response(command)
        return self._scan_response(request, command)

    def _status_response(self, command):
        if self._configuration_is_valid(require_window=False):
            return self._response("STATUS", command, "Interface ready.")
        return self._response(
            "NOT_READY",
            command,
            "Interface configuration is unavailable.",
        )

    def _scan_response(self, request, command):
        if not self._is_valid_scan_request(request):
            return self._response(
                "INVALID_INPUT",
                command,
                "Command or request cannot be processed.",
            )
        if not self._configuration_is_valid(require_window=True):
            return self._response(
                "INVALID_INPUT",
                command,
                "Command or request cannot be processed.",
            )

        try:
            subject_id = map_telegram_user_to_subject_id(
                request.telegram_user_id
            )
            window_id = self._window_id_provider(request)
        except Exception:
            return self._response(
                "INVALID_INPUT",
                command,
                "Command or request cannot be processed.",
            )

        if not self._is_non_blank_string(window_id):
            return self._response(
                "INVALID_INPUT",
                command,
                "Command or request cannot be processed.",
            )

        worker_completed = False

        def decorated_worker(*, state_path):
            nonlocal worker_completed
            try:
                result = self._worker(state_path=state_path)
            except BaseException as exc:
                raise _WorkerFailureMarker(exc) from exc
            worker_completed = True
            return result

        try:
            self._quota_slot_worker(
                subject_id=subject_id,
                window_id=window_id,
                quota_limit=self._quota_limit,
                slot_capacity=self._slot_capacity,
                quota_state_path=self._quota_state_path,
                worker_state_path=self._worker_state_path,
                quota_now_provider=self._quota_now_provider,
                reservation_id_provider=self._reservation_id_provider,
                worker=decorated_worker,
            )
        except QuotaSlotRejected as exc:
            return self._quota_rejection_response(command, exc.reason_code)
        except _WorkerFailureMarker as exc:
            if exc.__cause__ is exc._original_worker_error:
                return self._response(
                    "WORKER_FAILED",
                    command,
                    "Scan execution failed after admission.",
                )
            return self._response(
                "WORKER_AND_RELEASE_FAILED",
                command,
                "Scan execution and release handling failed.",
            )
        except BaseException:
            if worker_completed:
                return self._response(
                    "RELEASE_FAILED",
                    command,
                    "Scan completed but release handling failed.",
                )
            return self._response(
                "INTERNAL_ERROR",
                command,
                "Request could not be completed.",
            )

        return self._response("SCAN_SUCCESS", command, "Scan completed.")

    def _quota_rejection_response(self, command, reason_code):
        categories = {
            "QUOTA_EXHAUSTED": (
                "QUOTA_EXHAUSTED",
                "Current window quota is unavailable.",
            ),
            "SLOTS_FULL": ("SLOTS_FULL", "Scanner capacity is currently busy."),
            "STATE_CORRUPT": (
                "STATE_UNAVAILABLE",
                "Admission state is unavailable.",
            ),
        }
        category, message = categories.get(
            reason_code,
            ("ADMISSION_REJECTED", "Scan cannot be admitted."),
        )
        return self._response(category, command, message)

    def _response(self, category, command, message):
        return TelegramApplicationResponse(
            category=category,
            command=command,
            message=self._bound_message(message),
        )

    def _bound_message(self, message):
        if not self._is_valid_max_response_chars():
            return "Command or request cannot be processed."
        if len(message) <= self._max_response_chars:
            return message
        marker_length = len(TRUNCATION_MARKER)
        if self._max_response_chars > marker_length:
            prefix_length = self._max_response_chars - marker_length
            return message[:prefix_length] + TRUNCATION_MARKER
        return message[: self._max_response_chars]

    def _configuration_is_valid(self, *, require_window):
        if not self._is_positive_integer(self._quota_limit):
            return False
        if not self._is_positive_integer(self._slot_capacity):
            return False
        if self._quota_state_path is None or self._worker_state_path is None:
            return False
        if not callable(self._quota_now_provider):
            return False
        if not callable(self._reservation_id_provider):
            return False
        if not callable(self._quota_slot_worker) or not callable(self._worker):
            return False
        if not self._is_valid_max_response_chars():
            return False
        if require_window and not callable(self._window_id_provider):
            return False
        return True

    @staticmethod
    def _command_from_request(request):
        command = getattr(request, "command", "")
        return command if isinstance(command, str) else ""

    @staticmethod
    def _is_valid_scan_request(request):
        if not isinstance(request, TelegramCommandRequest):
            return False
        return request.arguments in (None, ())

    @staticmethod
    def _is_non_blank_string(value):
        return isinstance(value, str) and bool(value.strip())

    @staticmethod
    def _is_positive_integer(value):
        return type(value) is int and value > 0

    def _is_valid_max_response_chars(self):
        return (
            self._is_positive_integer(self._max_response_chars)
            and self._max_response_chars > len(TRUNCATION_MARKER)
        )
