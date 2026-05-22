from image2json.ollama_client import _extract_message_content


def test_extract_chat_message_content():
    data = {"message": {"role": "assistant", "content": '{"summary":"ok"}'}}
    assert _extract_message_content(data) == '{"summary":"ok"}'


def test_extract_generate_response_content_for_compatibility():
    data = {"response": '{"summary":"ok"}'}
    assert _extract_message_content(data) == '{"summary":"ok"}'
