import re

import pytest
from pytest_bdd import parsers, scenarios, then, when

from api.api_result import ApiResult
from api.posts_client import PostsClient
from config.settings import Settings

scenarios("api_posts.feature")

VALID_POST = {"title": "Boundary testing", "body": "Checking the baseline", "userId": 1}

# Words that show an error message is about the title's length (no documented wording to match).
TITLE_LENGTH_WORDS = ("length", "long", "short", "empty", "characters", "max", "min")


@pytest.fixture(scope="session")
def posts(new_api_context, settings: Settings) -> PostsClient:
    return PostsClient(new_api_context(settings.api_base_url))


def decode_unicode_codes(text: str) -> str:
    """Turn \\uXXXX codes from the feature file into the real (often invisible) characters."""
    return re.sub(r"\\u([0-9a-fA-F]{4})", lambda m: chr(int(m.group(1), 16)), text)


def _send(ctx, posts: PostsClient, payload) -> ApiResult:
    ctx["sent"] = payload
    ctx["result"] = posts.create(payload)
    return ctx["result"]


# ---- When ---------------------------------------------------------------
@when(parsers.re(r'I create a post with title "(?P<title>[^"]*)", body "(?P<body>[^"]*)" '
                 r'and userId (?P<user_id>"[^"]*"|\d+)'))
def create_post(ctx, posts, title, body, user_id):
    user_id = user_id.strip('"') if user_id.startswith('"') else int(user_id)
    _send(ctx, posts, {"title": title, "body": body, "userId": user_id})


@when(parsers.parse("I create a post with a title of {length:d} characters"))
def create_long_title(ctx, posts, length):
    _send(ctx, posts, {**VALID_POST, "title": "A" * length})


@when(parsers.re(r'I create a post with the title "(?P<title>.*)"$'))
def create_titled_post(ctx, posts, title):
    _send(ctx, posts, {**VALID_POST, "title": decode_unicode_codes(title)})


@when(parsers.parse('I create an otherwise valid post without the "{field}" field'))
def create_without_field(ctx, posts, field):
    payload = dict(VALID_POST)
    payload.pop(field)
    _send(ctx, posts, payload)


@when("I create a post with an empty JSON object")
def create_empty(ctx, posts):
    _send(ctx, posts, {})


@when("I send a malformed JSON body")
def send_malformed(ctx, posts):
    ctx["result"] = posts.create_raw('{"title": "unterminated", "userId": 1')


# ---- Then ---------------------------------------------------------------
@then("the request is rejected with a client error")
def rejected_with_client_error(ctx):
    result: ApiResult = ctx["result"]
    assert 400 <= result.status < 500, (
        f"accepted without validation: expected 4xx, got HTTP {result.status}: {result.text[:200]}"
    )


# No error format is documented, so these check the meaning of the message, not its exact wording.
@then(parsers.parse('the error message mentions "{word}"'))
def message_mentions(ctx, word):
    result: ApiResult = ctx["result"]
    assert word.lower() in result.text.lower(), (
        f"error message does not mention {word!r}: {result.text[:200]}"
    )


@then("the error message explains that the title length is invalid")
def title_length_message(ctx):
    message = ctx["result"].text.lower()
    assert "title" in message, f"error message does not mention the title: {message[:200]}"
    assert any(word in message for word in TITLE_LENGTH_WORDS), (
        f"error message does not explain the length problem: {message[:200]}"
    )


@then("the response echoes the title, body and userId that were sent")
def echoes_all(ctx):
    body = ctx["result"].json
    for key, value in ctx["sent"].items():
        assert body[key] == value, key


@then("the response contains a new post id")
def has_new_id(ctx):
    body = ctx["result"].json
    assert isinstance(body.get("id"), int) and body["id"] > 0, body


@then(parsers.parse("the response echoes a title of exactly {length:d} characters"))
def echoes_title_length(ctx, length):
    title = ctx["result"].json["title"]
    assert len(title) == length and title == ctx["sent"]["title"]


@then("the response echoes the title exactly as sent")
def echoes_title_exactly(ctx):
    assert ctx["result"].json["title"] == ctx["sent"]["title"]
