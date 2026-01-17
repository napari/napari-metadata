import numpy as np
import pytest


@pytest.fixture
def rng() -> np.random.Generator:
    return np.random.default_rng(0)


@pytest.fixture
def path(tmp_path) -> str:
    return str(tmp_path / 'test.zarr')
