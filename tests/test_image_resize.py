from io import BytesIO

from PIL import Image

from image2json.ollama_client import _image_bytes_for_ollama


def test_image_bytes_for_ollama_resizes_large_image(tmp_path):
    image_path = tmp_path / "large.jpg"
    Image.new("RGB", (2400, 1200), color="white").save(image_path)

    payload = _image_bytes_for_ollama(image_path, max_image_side=1200)

    with Image.open(BytesIO(payload)) as resized:
        assert resized.size == (1200, 600)


def test_image_bytes_for_ollama_can_disable_resize(tmp_path):
    image_path = tmp_path / "large.jpg"
    Image.new("RGB", (2400, 1200), color="white").save(image_path)

    payload = _image_bytes_for_ollama(image_path, max_image_side=0)

    assert payload == image_path.read_bytes()
