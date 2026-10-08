"""Unit tests for Arda's BPF kernel authority evidence."""

from unittest.mock import patch

from backend.services import arda_bpf_authority as authority


def _fixture():
    pins = {
        name: 100 + index
        for index, name in enumerate(authority.PINS)
    }

    program = {
        "id": 432,
        "type": "lsm",
        "name": authority.PROGRAM,
        "tag": authority.EXPECTED_TAG,
        "map_ids": [
            pins[name] for name in authority.PROGRAM_MAP_PINS
        ],
    }

    link = {
        "id": 6,
        "type": "tracing",
        "prog_id": 432,
        "prog_type": "lsm",
        "attach_type": "lsm_mac",
    }

    return pins, program, link


def _verify(pins, programs, links):
    def read_json(*args):
        if args == ("prog", "show"):
            return programs
        if args == ("link", "show"):
            return links
        if args[:3] == ("map", "show", "pinned"):
            name = args[3].rsplit("/", 1)[-1]
            return {"id": pins[name]}
        raise AssertionError(f"Unexpected bpftool call: {args}")

    with patch.object(authority, "_read_json", side_effect=read_json):
        return authority.verify_attachment()


def test_live_arda_attachment_is_verified():
    pins, program, link = _fixture()
    result = _verify(pins, [program], [link])
    assert result["verified"] is True
    assert result["program_id"] == 432
    assert result["link_id"] == 6


def test_pinned_maps_without_arda_link_are_refused():
    pins, program, _ = _fixture()
    assert _verify(pins, [program], [])["verified"] is False


def test_single_map_spoof_is_refused():
    pins, program, link = _fixture()
    program["map_ids"] = [pins["harmony_map"]]
    assert _verify(pins, [program], [link])["verified"] is False


def test_wrong_program_tag_is_refused():
    pins, program, link = _fixture()
    program["tag"] = "0000000000000000"
    assert _verify(pins, [program], [link])["verified"] is False


def test_unrelated_systemd_lsm_is_refused():
    pins, _, _ = _fixture()
    program = {
        "id": 21,
        "type": "lsm",
        "name": "restrict_filesystems",
        "tag": "e8932b6bae2b9745",
        "map_ids": [11],
    }
    link = {
        "id": 2,
        "prog_id": 21,
        "prog_type": "lsm",
        "attach_type": "lsm_mac",
    }
    assert _verify(pins, [program], [link])["verified"] is False


def test_unexpected_extra_map_is_refused():
    pins, program, link = _fixture()
    program["map_ids"].append(999)
    assert _verify(pins, [program], [link])["verified"] is False


def test_missing_map_pin_is_refused():
    pins, program, link = _fixture()
    del pins["harmony_map"]
    assert _verify(pins, [program], [link])["verified"] is False
