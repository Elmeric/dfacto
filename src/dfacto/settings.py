"""The DfactoSettings model.

The DfactoSettings model defines the dfacto application settings and make them
accessible throughout the application by exposing a dfacto_settings instance.
"""
import os
from pathlib import Path
from typing import TYPE_CHECKING

from win32com.shell import shell, shellcon  # noqa

from dfacto.util import settings
from dfacto.util.settings import Setting

if TYPE_CHECKING:
    from dfacto.util.settings import WinAppDirs

__all__ = ["dfacto_settings"]


class DfactoSettings(settings.Settings):
    """The DfactoSettings model definition.

    The DfactoSettings model is a specialization of the Settings singleton base
    class. It declares:
        a set of Setting descriptor corresponding to the Fotocop application
            settings,

    Class attributes:
        lastSource: key and info (kind, id, path and subDirs) on the last opened
            images' source.
        lastDestination: path to the last selected images' destination.
        lastImageNamingTemplate: key of the last selected images' naming template.
        lastDestinationNamingTemplate: key of the last selected images' destination
            naming template.
        lastNamingExtension: the last selected images' extension format.
        log_level: The global Fotocop application log level.
        window_position: the last Fotocop application windows top left corner.
        window_size: the last Fotocop application windows size.
        qt_scale_factor: A magnifying factor to increase the Fotocop application
            lisibility

    Attributes:
        appDirs: A WinAppDirs NamedTuple containing the user app
            directories paths.
        resources: Path to the UI resources directory (images, icons,..).
        templates: Path to the Jinja templates directory.
    """

    app_dirs: "WinAppDirs"
    resources: Path
    templates: Path

    _DEFAULT_LOGLEVEL = "DEBUG"

    last_profile: Setting = settings.Setting(default_value=None)
    profiles: Setting = settings.Setting(default_value=None)
    # default_company_folder = settings.Setting(default_value="C:/Users/T0018179/MyApp/Git/home/portable/DFacto")
    default_company_folder = settings.Setting(default_value="F:/Users/Documents/Dfacto")
    log_level: Setting = settings.Setting(default_value=_DEFAULT_LOGLEVEL)
    window_position: Setting = settings.Setting(default_value=(0, 0))
    window_size: Setting = settings.Setting(default_value=(1600, 800))
    qt_scale_factor: Setting = settings.Setting(default_value="1.0")

    def __init__(self, app_name: str) -> None:
        # Retrieve or create the user directories for the application.
        app_dirs = settings.get_app_dirs(app_name)

        super().__init__(app_dirs.user_data_dir / "settings")

        self.app_dirs = app_dirs
        self.resources = Path(__file__).resolve().parent.parent.parent / "resources"
        templates_dir = app_dirs.user_config_dir / "templates"
        templates_dir.mkdir(parents=True, exist_ok=True)
        self.templates = templates_dir

    def __repr__(self) -> str:
        """A pretty representation of a DfactoSettings.

        Returns:
            A string with the project path and all its spec items.
        """
        return (
            f"DfactoSettings({self.log_level}, {self.window_position}, "
            f"{self.window_size}, {self.qt_scale_factor})"
        )

    def reset_to_defaults(self) -> None:
        """Reset all settings to their default value."""
        for setting in self.all_keys():
            default_value = getattr(DfactoSettings, setting).default_value
            setattr(self, setting, default_value)


if os.environ.get("DFACTO_DEV", 0):
    dfacto_settings = DfactoSettings("dfacto_dev")
else:
    dfacto_settings = DfactoSettings("dfacto")
