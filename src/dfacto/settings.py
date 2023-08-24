# Copyright (c) 2023 Eric Lemoine
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

"""The DfactoSettings model.

The DfactoSettings model defines the dfacto application settings and make them
accessible throughout the application by exposing a dfacto_settings instance.
"""

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from dfacto import DEV_MODE, IS_FROZEN, TEST_MODE
from dfacto.backend import naming
from dfacto.util.settings import Setting, Settings, get_app_dirs

if TYPE_CHECKING:
    from dfacto.util.settings import WinAppDirs

__all__ = ["dfacto_settings"]

logger = logging.getLogger(__name__)


class DfactoSettings(Settings):
    """The DfactoSettings model definition.

    The DfactoSettings model is a specialization of the Settings singleton base
    class. It declares:
        a set of Setting descriptor corresponding to the Dfacto application
            settings,

    Class attributes:
        last_profile: name of the last opened company profile.
        profiles: a mapping of profile names to profiles descripion already created.
        lastInvoiceNamingTemplate: key of the last selected invoice naming template.
        lastDestinationNamingTemplate: key of the last selected invoice destination
            naming template.
        default_company_folder: Path to the default folder where to find or store
            company profiles.
        due_date_delta: delay before to remind a not paid invoice (in days).
        log_level: The global Dfacto application log level.
        window_position: the last Dfacto application windows top left corner.
        window_size: the last Dfacto application windows size.
        qt_scale_factor: A magnifying factor to increase the Dfacto application
            lisibility
        font_size: The base font size to use in the Dfacto application.

    Attributes:
        app_dirs: A WinAppDirs NamedTuple containing the user app directories paths.
        resources: Path to the UI resources directory (images, icons,..).
        templates: Path to the Jinja templates directory.
    """

    app_dirs: "WinAppDirs"
    resources: Path
    templates: Path

    DEFAULT_COMPANY_FOLDER = "C:/Users/T0018179/MyApp/Git/home/portable/DFacto"
    # DEFAULT_COMPANY_FOLDER = "F:/Users/Documents/Dfacto"
    DEFAULT_LOG_LEVEL = "INFO"
    DEFAULT_QT_SCALE_FACTOR = "1.0"
    DEFAULT_FONT_SIZE = 2

    last_profile: Setting = Setting(default_value=None)
    profiles: Setting = Setting(default_value=None)
    lastInvoiceNamingTemplate: Setting = Setting(
        default_value=naming.NamingTemplates.default_invoice_naming_template
    )
    lastDestinationNamingTemplate: Setting = Setting(
        default_value=naming.NamingTemplates.default_destination_naming_template
    )
    default_company_folder = Setting(default_value=DEFAULT_COMPANY_FOLDER)
    log_level: Setting = Setting(default_value=DEFAULT_LOG_LEVEL)
    window_position: Setting = Setting(default_value=(0, 0))
    window_size: Setting = Setting(default_value=(1600, 800))
    qt_scale_factor: Setting = Setting(default_value=DEFAULT_QT_SCALE_FACTOR)
    font_size: Setting = Setting(default_value=DEFAULT_FONT_SIZE)
    # locale: Setting = Setting(default_value="en_US")
    # locale: Setting = Setting(default_value="fr_FR")
    locale: Setting = Setting(default_value=None)

    def __init__(self, app_name: str) -> None:
        # Retrieve or create the user directories for the application.
        app_dirs = get_app_dirs(app_name)

        super().__init__(app_dirs.user_data_dir / "settings")

        self.app_dirs = app_dirs
        if IS_FROZEN:
            self.resources = Path(__file__).resolve().parent.parent / "resources"
        else:
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


if TEST_MODE:
    dfacto_settings = DfactoSettings("dfacto_test")
elif DEV_MODE:
    dfacto_settings = DfactoSettings("dfacto_dev")
else:
    dfacto_settings = DfactoSettings("dfacto")
