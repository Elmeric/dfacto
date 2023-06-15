r"""Basic tools to handle application settings.

It provides:
    A Settings base class to manage persistent application setttins as basic
        key/value pairs.
    A SettingsError exception to handle settings persistency errors.
    A Setting data descriptor to access the basic key/value pairs as class
        attributes (appSettings.keys['mySetting'] = value is replaced by
        appSettings.mySetting = value)
    A getAppDir convenient function to retrieve the standard windows' application
        directories in '%LOCALAPPDATA%\<appName>'
"""

from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any, NamedTuple, Optional, overload, cast

from dfacto.util.basicpatterns import Singleton

__all__ = ["Settings", "SettingsError", "Setting", "WinAppDirs", "get_app_dirs"]

logger = logging.getLogger(__name__)


class PathEncoder(json.JSONEncoder):
    """A JSONEncoder to encode a pathlib.Path objects in a JSON file.

    The Path object is encoded into a string using its as_posix() method or into
    an empty string if the path name is not defined.
    """

    def default(self, obj: Any) -> Any:
        """Overrides the JSONEncoder default encoding method.

        Non Path objects are passed to the JSONEncoder base class, raising a
        TypeError if its type is not supported by the base encoder.

        Args:
            obj: the object to JSON encode.

        Returns:
             The string-encoded Path object.
        """
        if isinstance(obj, Path):
            return obj.as_posix() if obj.name else ""
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, obj)


class SettingsError(Exception):
    """Exception raised on settings saving error."""

    pass


class Settings(object, metaclass=Singleton):
    """A base class to handle persistent application settings.

    Settings is a singleton: only one instance of settings may exist for an
    applcation.
    Settings key/value pairs are read from / save to a JSON file passed when
    creating the Settings instance.
    Settings interface mimics a (very) simplified Qt5 QSettings.

    Examples:
        appSettings = Settings('path/to/mySettingsFile.json')
        appSettings.setValue('mySetting', (100, 200))
        appSettings.value('mySetting', default_value=(0, 0))   # returns 100, 200
        appSettings.contains('mySetting')   # returns True
        appSettings.allKeys()   # returns ['mySetting']
        appSettings.remove('mySetting')
        appSettings.clear()

    Attributes:
        _settingsFile: the path to the persistent settings file.
        _keys: the settings key/value pairs container.
    """

    _keys: dict[str, Any]
    _settings_file: Path

    def __init__(self, settings_file: Path) -> None:
        self._settings_file = settings_file.with_suffix(".json")

        self._keys = self._load()

    def _load(self) -> dict[str, Any]:
        """Intialize the settings from its persistent JSON file.

        Returns:
            The key/value pairs read from the JSON file or an empty dict on
            loading errors.
        """
        try:
            with self._settings_file.open() as fh:
                keys = cast(dict[str, Any], json.load(fh))
            return keys
        except (FileNotFoundError, json.JSONDecodeError) as exc:
            logger.debug(f"Cannot load the settings file: {exc}")
            return dict()

    def save(self) -> None:
        """Save the settings key/value pairs on a JSON file.

        Use a dedicated JSONEncoder to handle pathlib.Path objects.

        Raises:
            A SettingsErrors exception on OS or JSON encoding errors.
        """
        try:
            with self._settings_file.open(mode="w") as fh:
                json.dump(self._keys, fh, indent=4, cls=PathEncoder)
        except (OSError, TypeError) as e:
            raise SettingsError(e)

    def value(self, key: str, default_value: Any = None) -> Any:
        """Returns the value for setting key.

        If the setting doesn't exist, returns default_value. If no default value
        is specified, None is returned.

        Args:
            key: The setting key to look for.
            default_value: The default value to be returned if key does not exist.

        Returns:
            The key value.
        """
        return self._keys.get(key, default_value)

    def set_value(self, key: str, value: Any) -> None:
        """Sets the value of setting key to value.

        If the key already exists, the previous value is overwritten.

        Args:
            key: The setting key to set.
            value: The value to set.
        """
        self._keys[key] = value

    def contains(self, key: str) -> bool:
        """Check if a given key exists.

        Args:
            key: the key to check existence.

        Returns:
            True if it exists a setting called key; False otherwise
        """
        return key in self._keys

    def remove(self, key: str) -> None:
        """Removes the setting key.

        No errors are raised if there is no setting called key.

        Args:
            key: the key to remove
        """
        if key in self._keys:
            del self._keys[key]

    def all_keys(self) -> list[str]:
        """Returns a list of all keys that can be read using the Settings object.

        Returns:
            The list of existing keys.
        """
        return list(self._keys)

    def clear(self) -> None:
        """Removes all entries associated to this Settings object."""
        self._keys = dict()


class Setting(object):
    """A data descriptor to simplify a key/value access in a Settings instance.

    The name of a Setting descriptor corrrespond to a key in the Settings
    instance container / persistent file.
    On creation, an optional default value can be set for the associated key.

    Examples:
        Class AppSettings(Settings):
            mySetting = Setting(default_value=(0, 0))

        appSettings = AppSettings('path/to/mySettingsFile.json')
        appSettings.mySetting   # returns 0, 0
        appSettings.mySetting = (100, 200)
        appSettings.mySetting   # returns 100, 200

    Attributes:
        defaultValue: an optional default value for the setting.
        _key: the settings key in the key/value pairs container.
    """

    _key: str
    default_value: Optional[Any]

    def __init__(self, default_value: Any = None) -> None:
        self.default_value = default_value

    def __set_name__(self, owner: type[Settings], name: str) -> None:
        """Save the Setting instance name to use as a Settings key.

        Args:
            owner: The class where the Setting descriptor instance is created.
            name: the Setting descriptor instance name.
        """
        self._key = name

    @overload
    def __get__(self, instance: None, owner: None) -> Any:
        ...

    @overload
    def __get__(self, instance: Settings, owner: type[Settings]) -> Any:
        ...

    def __get__(
        self, instance: Optional[Settings], owner: Optional[type[Settings]]
    ) -> Any:
        """Descriptor getter.

        On get access, the descriptor returns the value associated to its key by
        reading the Settings instance key/value pair.

        Args:
            instance: the Settings instance owning the Setting descriptor.
            owner: The Settings class owning the Setting descriptor.

        Returns:
            The value for the Setting descriptor key.
        """
        if instance is None:
            return self
        return instance.value(self._key, self.default_value)

    def __set__(self, instance: Settings, value: Any) -> None:
        """Descriptor setter.

        On set access, the descriptor set the value of its key by writing in
        the associated Settings instance key/value pair.

        Args:
            instance: the Settings instance owning the Setting descriptor.
            value: the value to set.
        """
        instance.set_value(self._key, value)


class WinAppDirs(NamedTuple):
    """Paths of the default Windows user directories for the application."""

    user_data_dir: Path
    user_config_dir: Path
    user_cache_dir: Path
    user_log_dir: Path


def get_app_dirs(app_name: str, roaming: bool = False) -> WinAppDirs:
    r"""Returns the default Windows user directories for the application.

    Win 7 (roaming): %APPDATA%\<appName>
    Win 7 (not roaming): %LOCALAPPDATA%\<appName>

    Fallback to %HOMEPATH%\<appName> if the APPDATA or LOCALAPPDATA Windows environment
    variables are not found.
    The directories are created if required.

    Args:
        app_name: the application name. This should be properly capitalized
             and can contain whitespace.
        roaming: controls if the folder should be roaming or not on Windows.

    Returns:
        A WinAppDirs NamedTuple containing the user app directories paths.
    """
    folder: str | Path | None
    key = roaming and "APPDATA" or "LOCALAPPDATA"
    folder = os.environ.get(key)

    if folder is None:
        folder = Path.home()
    folder = Path(folder)

    user_data_dir = folder / app_name
    user_data_dir.mkdir(parents=True, exist_ok=True)

    user_config_dir = user_data_dir / "Config"
    user_config_dir.mkdir(parents=True, exist_ok=True)

    user_cache_dir = user_data_dir / "Cache"
    user_cache_dir.mkdir(parents=True, exist_ok=True)

    user_log_dir = user_data_dir / "Logs"
    user_log_dir.mkdir(parents=True, exist_ok=True)

    return WinAppDirs(user_data_dir, user_config_dir, user_cache_dir, user_log_dir)
