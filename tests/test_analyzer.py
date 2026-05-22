from PIL import Image

from image2json.analyzer import _read_image_metadata


def test_read_image_metadata(tmp_path):
    image_path = tmp_path / "sample.jpg"
    Image.new("RGB", (120, 80), color="white").save(image_path)

    metadata = _read_image_metadata(image_path)

    assert metadata == {
        "width": 120,
        "height": 80,
        "orientation": "landscape",
        "aspect_ratio": 1.5,
    }
