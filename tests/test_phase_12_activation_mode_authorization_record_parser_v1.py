from __future__ import annotations
import builtins, importlib, importlib.resources, inspect, os, pathlib, tempfile
from datetime import datetime, timezone
import pytest
from engine.phase_12_activation_mode_authorization_verifier_v1 import Phase12ActivationAuthorizationRecordV1

MODULE_NAME = "engine.phase_12_activation_mode_authorization_record_parser_v1"
ERROR_TEXT = "INVALID_AUTHORIZATION_RECORD_DOCUMENT"
MODES = ("CREDENTIAL_VALIDATION", "TELEGRAM_CONNECTIVITY_VALIDATION", "TELEGRAM_START_VALIDATION", "CONTROLLED_WORKLOAD")
BASE = {"schema_version":"phase12-activation-authorization-record-v1", "mode":"CREDENTIAL_VALIDATION", "owner_authorization_id":"owner-a", "checkpoint_id":"checkpoint-a", "approved_locked_commit":"a"*40, "approval_timestamp_utc":"2026-07-22T12:00:00Z", "expires_at_utc":"2026-07-22T12:05:00Z", "accepted_locked_commit":"b"*40}
KEYS = tuple(BASE)

def api():
    m = importlib.import_module(MODULE_NAME)
    return m.Phase12ActivationAuthorizationRecordDocumentErrorV1, m.parse_phase_12_activation_authorization_record_v1

def doc(**changes):
    values = dict(BASE); values.update(changes)
    return "".join(f"{k}={values[k]}\n" for k in KEYS)

def rejects(value):
    error, parser = api()
    with pytest.raises(error) as caught: parser(document=value)
    assert str(caught.value) == ERROR_TEXT and caught.value.args == (ERROR_TEXT,)

def test_public_api_is_exact():
    error, parser = api(); assert error.__name__ == "Phase12ActivationAuthorizationRecordDocumentErrorV1"; assert parser.__name__ == "parse_phase_12_activation_authorization_record_v1"
    sig = inspect.signature(parser); assert tuple(sig.parameters) == ("document",); assert sig.parameters["document"].kind is inspect.Parameter.KEYWORD_ONLY; assert sig.return_annotation is not inspect.Signature.empty

@pytest.mark.parametrize("mode", MODES)
def test_each_accepted_mode_parses(mode):
    _, parser = api(); record = parser(document=doc(mode=mode)); assert isinstance(record, Phase12ActivationAuthorizationRecordV1) and record.mode == mode

def test_valid_mapping_and_utc_conversion():
    _, parser = api(); r = parser(document=doc())
    assert (r.mode, r.owner_authorization_id, r.checkpoint_id) == (BASE["mode"], "owner-a", "checkpoint-a")
    assert (r.approved_locked_commit, r.accepted_locked_commit) == ("a"*40, "b"*40)
    assert r.approval_timestamp_utc == datetime(2026,7,22,12,tzinfo=timezone.utc) and r.expires_at_utc == datetime(2026,7,22,12,5,tzinfo=timezone.utc)

def test_identifier_boundaries_and_distinct_commits():
    _, parser = api(); lo = parser(document=doc(owner_authorization_id="a", checkpoint_id="b")); hi = parser(document=doc(owner_authorization_id="a"*64, checkpoint_id="b"*64)); assert lo.owner_authorization_id == "a" and hi.checkpoint_id == "b"*64 and lo.approved_locked_commit != lo.accepted_locked_commit

def test_output_is_immutable_slotted_and_sanitized():
    _, parser = api(); r = parser(document=doc()); assert not hasattr(r,"__dict__") and repr(r) == "Phase12ActivationAuthorizationRecordV1()"
    with pytest.raises((AttributeError,TypeError)): r.mode = "changed"
    with pytest.raises((AttributeError,TypeError)): r.extra = "changed"

def test_repeat_parse_is_equal_and_not_authorization():
    _, parser = api(); a = parser(document=doc()); b = parser(document=doc()); assert a == b and not hasattr(a,"authorized") and not hasattr(a,"policy")

@pytest.mark.parametrize("value", [None,b"", "", "schema_version=x\n", doc().rstrip("\n"), doc()+"\n", doc().replace("\n","\r\n"), doc().replace("\n","\r"), "\ufeff"+doc(), doc().replace("mode=","mode=\x00"), doc()+"comment=x\n"])
def test_document_line_and_type_rejections(value): rejects(value)

@pytest.mark.parametrize("value", [doc().replace("mode=CREDENTIAL_VALIDATION","Mode=CREDENTIAL_VALIDATION"), doc().replace("mode=CREDENTIAL_VALIDATION","mode=CREDENTIAL_VALIDATION=x"), doc().replace("mode=CREDENTIAL_VALIDATION","mode =CREDENTIAL_VALIDATION"), doc().replace("mode=CREDENTIAL_VALIDATION","mode="), doc().replace("schema_version=phase12-activation-authorization-record-v1","schema_version=unknown"), doc().replace("schema_version=phase12-activation-authorization-record-v1","schema_version=phase12-activation-authorization-record-v1 ")])
def test_schema_key_delimiter_and_version_rejections(value): rejects(value)

@pytest.mark.parametrize("mode", ["CLOSED","PRODUCTION","unknown","credential_validation"," CREDENTIAL_VALIDATION",""])
def test_mode_rejections(mode): rejects(doc(mode=mode))

@pytest.mark.parametrize("field,value", [("owner_authorization_id",""),("owner_authorization_id"," owner-a"),("owner_authorization_id","owner-a "),("owner_authorization_id","owner a"),("owner_authorization_id","owner/a"),("owner_authorization_id","a"*65),("checkpoint_id",""),("checkpoint_id","checkpoint/a"),("checkpoint_id","b"*65)])
def test_identifier_rejections(field,value): rejects(doc(**{field:value}))

@pytest.mark.parametrize("field,value", [("approved_locked_commit","a"*39),("approved_locked_commit","a"*41),("approved_locked_commit","A"*40),("approved_locked_commit","g"*40),("approved_locked_commit","sha1:"+"a"*40),("approved_locked_commit"," a"*20),("accepted_locked_commit",""),("accepted_locked_commit","b"*39),("accepted_locked_commit","B"*40)])
def test_commit_rejections(field,value): rejects(doc(**{field:value}))

@pytest.mark.parametrize("field,value", [("approval_timestamp_utc","2026-02-30T12:00:00Z"),("approval_timestamp_utc","2026-07-22T12:00:00"),("approval_timestamp_utc","2026-07-22T12:00:00+00:00"),("approval_timestamp_utc"," 2026-07-22T12:00:00Z"),("approval_timestamp_utc","2026-07-22T12:00:00.1Z"),("expires_at_utc","2026-07-22T12:00:00Z")])
def test_timestamp_rejections(field,value):
    changes = {field:value}
    if field == "expires_at_utc": changes["approval_timestamp_utc"] = value
    rejects(doc(**changes))

def test_error_is_fixed_and_does_not_disclose_evidence():
    error, parser = api()
    with pytest.raises(error) as caught: parser(document=doc(mode="bad", owner_authorization_id="synthetic-owner"))
    assert str(caught.value) == ERROR_TEXT and "synthetic-owner" not in repr(caught.value) and "bad" not in repr(caught.value)

class Hostile(str):
    def split(self,*a,**k): raise RuntimeError("hostile")
    def splitlines(self,*a,**k): raise RuntimeError("hostile")
class BaseHostile(str):
    def split(self,*a,**k): raise KeyboardInterrupt()
    def splitlines(self,*a,**k): raise KeyboardInterrupt()

def test_unexpected_ordinary_exception_propagates():
    _, parser = api()
    with pytest.raises(RuntimeError, match="^hostile$"): parser(document=Hostile(doc()))

def test_base_exception_propagates():
    _, parser = api()
    with pytest.raises(KeyboardInterrupt): parser(document=BaseHostile(doc()))

class _ForbiddenFilesystemAccess:
    def __call__(self, *args, **kwargs):
        raise AssertionError("parser attempted filesystem access")

def test_parser_has_no_effectful_import_or_filesystem_surface(monkeypatch):
    module = importlib.import_module(MODULE_NAME)
    forbidden_globals = {"os", "pathlib", "subprocess", "socket", "logging", "random", "uuid", "requests", "tempfile"}
    assert not forbidden_globals.intersection(vars(module))
    blocked = _ForbiddenFilesystemAccess()
    monkeypatch.setattr(builtins, "open", blocked)
    monkeypatch.setattr(os, "open", blocked)
    monkeypatch.setattr(pathlib.Path, "open", blocked)
    monkeypatch.setattr(pathlib.Path, "read_text", blocked)
    monkeypatch.setattr(pathlib.Path, "read_bytes", blocked)
    monkeypatch.setattr(tempfile, "NamedTemporaryFile", blocked)
    monkeypatch.setattr(tempfile, "TemporaryFile", blocked)
    monkeypatch.setattr(tempfile, "mkstemp", blocked)
    monkeypatch.setattr(tempfile, "mkdtemp", blocked)
    monkeypatch.setattr(importlib.resources, "files", blocked)
    _, parser = api()
    assert isinstance(parser(document=doc()), Phase12ActivationAuthorizationRecordV1)
