from dataclasses import FrozenInstanceError

import pytest

from src.crawler.config import CrawlConfig, validate_config


def test_config_is_an_immutable_value() -> None:
    config = CrawlConfig(start=1, end=5, concurrency=2)

    assert validate_config(config) is None
    assert not hasattr(config, "__dict__")
    frozen_field = "start"
    with pytest.raises(FrozenInstanceError):
        setattr(config, frozen_field, 2)
