"""Sign-in: passwords, sessions, lockout after repeated failures, and single sign-on over OpenID Connect
(Microsoft Entra ID, Google, Keycloak, Dex ...). Pure: no database, no network."""
from __future__ import annotations

import base64
import hashlib
import os
import sys
import time
from urllib.parse import parse_qs, urlparse

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app import auth  # noqa: E402


# ------------------------------------------------------------------ passwords
def test_a_password_is_stored_salted_and_checks_only_against_itself():
    h = auth.hash_password("correct horse battery")
    assert h.startswith("scrypt$") and "correct" not in h
    assert h != auth.hash_password("correct horse battery")          # a new salt every time
    assert auth.verify_password("correct horse battery", h)
    assert not auth.verify_password("correct horse batterY", h)
    assert not auth.verify_password("x", "") and not auth.verify_password("x", "garbage")


def test_a_short_password_is_refused_with_a_reason():
    assert auth.password_problems("short") and auth.password_problems("") and auth.password_problems(None)
    assert auth.password_problems("long enough pass") == []


# ------------------------------------------------------------------ sessions
def test_a_session_token_is_random_and_only_its_hash_is_kept():
    tok, digest = auth.new_token()
    tok2, _ = auth.new_token()
    assert tok != tok2 and len(tok) >= 40
    assert digest == auth.digest(tok) and tok not in digest


def test_a_session_expires():
    s = {"created_at": 1000.0, "expires_at": 1000.0 + auth.SESSION_HOURS * 3600}
    assert auth.session_alive(s, now=1001.0)
    assert not auth.session_alive(s, now=s["expires_at"] + 1)


# ------------------------------------------------------------------ lockout
def test_five_wrong_passwords_lock_the_account_for_a_while_then_it_opens():
    t = auth.Throttle()
    for i in range(auth.Throttle.LIMIT):
        assert not t.blocked("a@x.co", now=100 + i)
        t.fail("a@x.co", now=100 + i)
    assert t.blocked("a@x.co", now=110)
    assert not t.blocked("b@x.co", now=110)                      # only that account
    assert not t.blocked("a@x.co", now=110 + auth.Throttle.WINDOW_S + 1)


def test_a_good_sign_in_clears_the_count():
    t = auth.Throttle()
    for i in range(auth.Throttle.LIMIT - 1):
        t.fail("a@x.co", now=100)
    t.succeed("a@x.co")
    t.fail("a@x.co", now=101)
    assert not t.blocked("a@x.co", now=102)


# ------------------------------------------------------------------ single sign-on (OpenID Connect)
META = {"issuer": "https://idp.example", "authorization_endpoint": "https://idp.example/auth",
        "token_endpoint": "https://idp.example/token", "jwks_uri": "https://idp.example/keys"}


def test_pkce_challenge_is_the_s256_of_the_verifier():
    verifier, challenge = auth.pkce()
    want = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    assert challenge == want and 43 <= len(verifier) <= 128


def test_the_sign_in_link_carries_state_nonce_and_pkce():
    url = auth.authorize_url(META, "radarops", "http://radar/api/v1/auth/sso/callback", state="S", nonce="N", challenge="C")
    q = {k: v[0] for k, v in parse_qs(urlparse(url).query).items()}
    assert url.startswith("https://idp.example/auth?")
    assert q == {"response_type": "code", "client_id": "radarops", "redirect_uri": "http://radar/api/v1/auth/sso/callback",
                 "scope": "openid email profile", "state": "S", "nonce": "N", "code_challenge": "C", "code_challenge_method": "S256"}


@pytest.fixture(scope="module")
def idp_key():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    jwk = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    return key, {"keys": [{**jwk, "kid": "k1", "use": "sig", "alg": "RS256"}]}


def id_token(key, **over):
    now = int(time.time())
    claims = {"iss": "https://idp.example", "aud": "radarops", "sub": "u-1", "email": "nok@sit.kmutt.ac.th",
              "name": "Nok", "nonce": "N", "iat": now, "exp": now + 300, **over}
    return jwt.encode(claims, key, algorithm="RS256", headers={"kid": "k1"})


def test_a_genuine_id_token_gives_the_persons_identity(idp_key):
    key, jwks = idp_key
    claims = auth.verify_id_token(id_token(key), jwks, issuer="https://idp.example", client_id="radarops", nonce="N")
    assert auth.identity(claims) == {"subject": "u-1", "email": "nok@sit.kmutt.ac.th", "name": "Nok", "verified": True}
    assert auth.identity({**claims, "email_verified": False})["verified"] is False


@pytest.mark.parametrize("over, why", [({"iss": "https://evil.example"}, "issuer"), ({"aud": "someone-else"}, "audience"),
                                       ({"nonce": "replayed"}, "nonce"), ({"exp": int(time.time()) - 600}, "expired")])
def test_an_id_token_from_elsewhere_for_someone_else_replayed_or_old_is_refused(idp_key, over, why):
    key, jwks = idp_key
    with pytest.raises(auth.AuthError):
        auth.verify_id_token(id_token(key, **over), jwks, issuer="https://idp.example", client_id="radarops", nonce="N")


def test_an_id_token_signed_by_another_key_is_refused(idp_key):
    _, jwks = idp_key
    other = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    with pytest.raises(auth.AuthError):
        auth.verify_id_token(id_token(other), jwks, issuer="https://idp.example", client_id="radarops", nonce="N")


def test_an_unsigned_id_token_is_refused(idp_key):
    _, jwks = idp_key
    unsigned = jwt.encode({"iss": "https://idp.example", "aud": "radarops", "sub": "x", "nonce": "N",
                           "exp": int(time.time()) + 60}, key=None, algorithm="none")
    with pytest.raises(auth.AuthError):
        auth.verify_id_token(unsigned, jwks, issuer="https://idp.example", client_id="radarops", nonce="N")


def test_identity_falls_back_to_the_username_when_the_idp_sends_no_email():
    assert auth.identity({"sub": "9", "preferred_username": "nok@corp.co"})["email"] == "nok@corp.co"


def test_a_group_from_the_idp_picks_the_role_first_rule_wins_else_the_default():
    rules = [{"claim": "groups", "value": "radarops-admins", "role": "admin"},
             {"claim": "groups", "value": "sre", "role": "developer"},
             {"claim": "roles", "value": "Manager", "role": "management"}]
    assert auth.role_for({"groups": ["staff", "sre"]}, rules, "viewer") == "developer"
    assert auth.role_for({"groups": ["sre", "radarops-admins"]}, rules, "viewer") == "admin"
    assert auth.role_for({"roles": "Manager"}, rules, "viewer") == "management"
    assert auth.role_for({"groups": ["staff"]}, rules, "viewer") == "viewer"


def test_only_allowed_email_domains_may_sign_in_when_a_list_is_set():
    assert auth.domain_allowed("nok@sit.kmutt.ac.th", "kmutt.ac.th, example.co.th")
    assert auth.domain_allowed("p@example.co.th", "kmutt.ac.th, example.co.th")
    assert not auth.domain_allowed("x@gmail.com", "kmutt.ac.th")
    assert not auth.domain_allowed("x@evilkmutt.ac.th", "kmutt.ac.th")
    assert auth.domain_allowed("anyone@anywhere.io", "")
