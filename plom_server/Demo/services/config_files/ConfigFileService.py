# SPDX-License-Identifier: AGPL-3.0-or-later
# Copyright (C) 2023 Edith Coates
# Copyright (C) 2023 Andrew Rechnitzer

"""Handle building a server database from a config file."""

from typing import Union, Optional, NewType, List
from pathlib import Path
import sys
from dataclasses import dataclass, asdict

if sys.version_info < (3, 11):
    import tomli as tomllib
else:
    import tomllib

from . import PlomConfigError


@dataclass()
class DemoBundleConfig:
    """A description of a demo bundle that can be generated using artificial data."""

    first_paper: int
    last_paper: int
    extra_page_papers: Optional[List[int]] = None
    scrap_page_papers: Optional[List[int]] = None
    garbage_page_papers: Optional[List[int]] = None
    wrong_version_papers: Optional[List[int]] = None
    duplicate_page_papers: Optional[List[int]] = None
    discard_pages: Optional[List[int]] = None


@dataclass()
class DemoHWBundleConfig:
    """A description of a demo homework bundle that can be generated using artificial data."""

    paper_number: int
    pages: List[List[int]]


@dataclass()
class PlomServerConfig:
    """A description of a Plom server's database.

    Can be saved to a .toml file, or loaded from a toml to quickly spin up a server with a pre-defined state.
    """

    parent_dir: Optional[Path] = None
    test_spec: Optional[Union[str, Path]] = None
    test_sources: Optional[Union[str, List[Path]]] = None
    prenaming_enabled: bool = False
    classlist: Optional[Union[str, Path]] = None
    num_to_produce: Optional[int] = None
    qvmap: Optional[Union[str, Path]] = None
    bundles: Optional[List[DemoBundleConfig]] = None
    hw_bundles: Optional[List[DemoHWBundleConfig]] = None

    def __post__init(self):
        """Validate the config beyond type checking."""
        all_instance_fields = asdict(self)
        if self.test_spec is None and not all(
            f is None for f in all_instance_fields.values()
        ):
            raise PlomConfigError(
                "A test specification is required in order to build a server."
            )

        if self.bundles is None and self.hw_bundles is None:
            if self.test_sources is None:
                raise PlomConfigError(
                    "Bundles are specified but the config lacks a test_sources field."
                )
            if self.num_to_produce is None and self.qvmap is None:
                raise PlomConfigError(
                    "Bundles are specified but the config lacks a qvmap or num_to_produce field."
                )


def read_server_config(path: Union[str, Path]) -> PlomServerConfig:
    """Create a server config from a TOML file.

    Args:
        path (string or Path-like): location of the config toml file

    Returns:
        PlomServerConfig: a server config.
    """
    with open(path, "rb") as config_file:
        try:
            config = tomllib.load(config_file)
            config["parent_dir"] = Path(path).parent
            return PlomServerConfig(**config)
        except tomllib.TOMLDecodeError as e:
            raise ValueError(e)


def read_server_config_from_string(
    config: str, parent_dir: Path = None
) -> PlomServerConfig:
    """Create a server config from a TOML-formatted string."""
    try:
        config = tomllib.loads(config)
        config["parent_dir"] = parent_dir
        print(config)
        return PlomServerConfig(**config)
    except tomllib.TOMLDecodeError as e:
        raise ValueError(e)
