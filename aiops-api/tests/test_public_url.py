"""The public address people reach the app at: one written form for the path, nothing odd let through. Pure."""
from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import public_url as pu  # noqa: E402


@pytest.mark.parametrize("raw", ["/capstone26/cp26pt1", "/capstone26/cp26pt1/", "/capstone26/cp26pt1//"])
def test_a_folder_is_always_written_with_one_slash_at_the_end(raw):
    assert pu.folder(raw) == "/capstone26/cp26pt1/"


def test_the_root_is_one_slash():
    assert pu.folder("") == pu.folder("/") == "/"


@pytest.mark.parametrize("bad", ["capstone26/", "/a/../b/", "/./a/", "//evil.example/", "/a//b/", "/a; domain=evil.example/", "/a b/",
                                 "/a%2e%2e/", "/a?x=1", "/a#x", "/a\r\nSet-Cookie: x=1/", "/.hidden/", "/" + "a" * 300, None])
def test_anything_else_is_not_a_folder(bad):
    assert pu.folder(bad) is None


@pytest.mark.parametrize("raw", ["https://public.example/capstone26/cp26pt1", "https://public.example/capstone26/cp26pt1/",
                                 " https://Public.Example:443/capstone26/cp26pt1// "])
def test_the_public_address_has_one_form(raw):
    p = pu.parse(raw)
    assert (p.base, p.path, p.host, p.https) == ("https://public.example/capstone26/cp26pt1", "/capstone26/cp26pt1/", "public.example", True)


@pytest.mark.parametrize("raw", ["https://public.example", "https://public.example/", "https://public.example/a/"])
def test_an_address_is_joined_without_a_double_slash(raw):
    p = pu.parse(raw)
    assert p.join("/#/login") == p.join("#/login") == raw.rstrip("/") + "/#/login"
    assert "//" not in p.join("api/v1/x").split("://")[1]


def test_a_port_is_part_of_the_host():
    p = pu.parse("https://cp.example:8443")
    assert (p.base, p.host, p.path) == ("https://cp.example:8443", "cp.example:8443", "/")


@pytest.mark.parametrize("bad", ["", None, "public.example/a", "ftp://public.example", "javascript:alert(1)", "https:///a",
                                 "https://user:pw@public.example/a", "https://public.example/a?x=1", "https://public.example/a#x",
                                 "https://public.example/a/../b", "https://public.example:notaport/"])
def test_a_value_that_is_not_a_plain_address_is_not_used(bad):
    assert pu.parse(bad) is None


def test_a_request_is_public_only_when_its_host_is_exactly_the_public_one():
    p = pu.parse("https://public.example/a")
    assert p.serves("public.example") and p.serves("PUBLIC.example:443")
    for other in ("cp.example:8080", "evil.public.example", "public.example.evil.com", "public.example:8080", "", None):
        assert not p.serves(other)


def test_only_our_own_proxies_are_believed():
    assert pu.trusted_proxy("127.0.0.1") and pu.trusted_proxy("172.18.0.5")
    for other in ("10.4.1.2", "202.44.9.103", "8.8.8.8", "testclient", "", None):
        assert not pu.trusted_proxy(other)
